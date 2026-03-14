"""
OMEGA Hardware Benchmark v1.0 — Meet alle 8 systeemcomponenten.

Componenten:
  1. CPU/RAM baseline (psutil)
  2. GPU status (nvidia-smi + torch VRAM)
  3. SQLite performance (CorticalStack read/write)
  4. Embedding speed (Voyage encode)
  5. LLM latency (Groq API probe)
  6. L1 Pulse (FastAPI health)
  7. L3 Deep Scan (FastAPI deep health)
  8. SwarmEngine throughput (agent dispatch)

Output: data/benchmark_results.json + terminal rapport
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# --- Project bootstrap ---
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RESULTS_PATH = DATA_DIR / "benchmark_results.json"

# Kleuren (simpel)
G = "\033[92m"  # groen
Y = "\033[93m"  # geel
C = "\033[96m"  # cyaan
R = "\033[91m"  # rood
W = "\033[97m"  # wit
RESET = "\033[0m"


def _header(title: str) -> None:
    """Toon een benchmark sectie header."""
    print(f"\n{C}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{RESET}")


def _result(label: str, value: str, unit: str = "", ok: bool = True) -> None:
    """Toon een benchmark resultaatregel."""
    color = G if ok else Y
    print(f"  {color}[{'OK' if ok else '!!'}]{RESET} {label:<30} {W}{value}{RESET} {unit}")


# ==================== BENCHMARK FUNCTIES ====================

def bench_cpu_ram() -> dict:
    """1. CPU/RAM baseline via psutil."""
    try:
        import psutil
    except ImportError:
        logger.debug("psutil niet beschikbaar")
        return {"error": "psutil niet beschikbaar"}
    cpu_count = os.cpu_count() or 4
    cpu_freq = psutil.cpu_freq()
    cpu_percent = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()

    result = {
        "cpu_cores": cpu_count,
        "cpu_freq_mhz": round(cpu_freq.current) if cpu_freq else 0,
        "cpu_freq_max_mhz": round(cpu_freq.max) if cpu_freq else 0,
        "cpu_percent": cpu_percent,
        "ram_total_gb": round(ram.total / (1024**3), 1),
        "ram_used_gb": round(ram.used / (1024**3), 1),
        "ram_percent": ram.percent,
    }

    _header("1. CPU / RAM BASELINE")
    _result("CPU Cores", str(cpu_count))
    _result("CPU Freq", f"{result['cpu_freq_mhz']}", "MHz")
    _result("CPU Usage", f"{cpu_percent}%", "", cpu_percent < 80)
    _result("RAM Total", f"{result['ram_total_gb']}", "GB")
    _result("RAM Used", f"{result['ram_used_gb']}", f"GB ({ram.percent}%)", ram.percent < 85)

    return result


def bench_gpu() -> dict:
    """2. GPU status via nvidia-smi + torch."""
    _header("2. GPU STATUS")

    result = {"available": False}

    # nvidia-smi data
    try:
        proc = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=name,clocks.gr,clocks.max.gr,clocks.mem,clocks.max.mem,"
             "power.draw,power.limit,pstate,temperature.gpu,memory.total,memory.used,memory.free",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0:
            parts = [p.strip() for p in proc.stdout.strip().split(",")]
            if len(parts) >= 12:
                result = {
                    "available": True,
                    "gpu_name": parts[0],
                    "clock_mhz": int(parts[1].replace(" MHz", "")),
                    "clock_max_mhz": int(parts[2].replace(" MHz", "")),
                    "mem_clock_mhz": int(parts[3].replace(" MHz", "")),
                    "mem_clock_max_mhz": int(parts[4].replace(" MHz", "")),
                    "power_w": float(parts[5].replace(" W", "")),
                    "power_limit_w": float(parts[6].replace(" W", "")),
                    "pstate": parts[7],
                    "temp_c": int(parts[8].replace(" C", "")),
                    "vram_total_mb": int(parts[9].replace(" MiB", "")),
                    "vram_used_mb": int(parts[10].replace(" MiB", "")),
                    "vram_free_mb": int(parts[11].replace(" MiB", "")),
                }
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as e:
        result["error"] = str(e)

    if result["available"]:
        _result("GPU", result["gpu_name"])
        _result("Clock", f"{result['clock_mhz']}/{result['clock_max_mhz']}", "MHz")
        _result("Memory Clock", f"{result['mem_clock_mhz']}/{result['mem_clock_max_mhz']}", "MHz")
        _result("Power", f"{result['power_w']:.1f}/{result['power_limit_w']:.0f}", "W")
        _result("P-State", result["pstate"])
        _result("Temperature", f"{result['temp_c']}", "C", result["temp_c"] < 80)
        _result("VRAM Total", f"{result['vram_total_mb']}", "MiB")
        _result("VRAM Used", f"{result['vram_used_mb']}", "MiB")
        _result("VRAM Free", f"{result['vram_free_mb']}", "MiB", result["vram_free_mb"] > 1500)
    else:
        _result("GPU", "NIET BESCHIKBAAR", ok=False)

    return result


def bench_sqlite() -> dict:
    """3. SQLite performance — CorticalStack read/write speed."""
    _header("3. SQLITE PERFORMANCE")

    db_path = DATA_DIR / "cortical_stack.db"
    result = {"db_exists": db_path.exists()}

    if not db_path.exists():
        _result("CorticalStack DB", "NIET GEVONDEN", ok=False)
        return result

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-65536")  # 64 MB
    conn.execute("PRAGMA mmap_size=268435456")  # 256 MB

    # Count events
    row = conn.execute("SELECT COUNT(*) FROM episodic_memory").fetchone()
    event_count = row[0] if row else 0
    result["event_count"] = event_count

    # Table overview
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    result["tables"] = len(tables)

    # READ benchmark: fetch last 1000 events
    t0 = time.perf_counter()
    rows = conn.execute(
        "SELECT id, actor, action, details, timestamp FROM episodic_memory ORDER BY id DESC LIMIT 1000"
    ).fetchall()
    read_ms = (time.perf_counter() - t0) * 1000
    result["read_1000_ms"] = round(read_ms, 2)

    # READ benchmark: full table count
    t0 = time.perf_counter()
    conn.execute("SELECT COUNT(*) FROM episodic_memory").fetchone()
    count_ms = (time.perf_counter() - t0) * 1000
    result["count_all_ms"] = round(count_ms, 2)

    # WRITE benchmark: insert + rollback (non-destructive)
    t0 = time.perf_counter()
    try:
        conn.execute("BEGIN")
        for i in range(100):
            conn.execute(
                "INSERT INTO episodic_memory (actor, action, details, timestamp) VALUES (?, ?, ?, ?)",
                ("benchmark", "test", f'{{"iteration": {i}}}', datetime.now().isoformat()),
            )
        conn.execute("ROLLBACK")
    except Exception:
        conn.execute("ROLLBACK")
    write_ms = (time.perf_counter() - t0) * 1000
    result["write_100_ms"] = round(write_ms, 2)

    # DB file size
    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    result["db_size_mb"] = round(db_size_mb, 1)

    conn.close()

    _result("Events", f"{event_count:,}")
    _result("DB Size", f"{db_size_mb:.1f}", "MB")
    _result("Read 1000", f"{read_ms:.2f}", "ms", read_ms < 50)
    _result("Count All", f"{count_ms:.2f}", "ms", count_ms < 20)
    _result("Write 100 (rollback)", f"{write_ms:.2f}", "ms", write_ms < 50)

    return result


def bench_embedding() -> dict:
    """4. Embedding speed — Voyage encode."""
    _header("4. EMBEDDING PERFORMANCE")

    result = {"available": False}

    try:
        from danny_toolkit.core.embeddings import get_embedder
        embedder = get_embedder()
        result["available"] = True
        result["provider"] = type(embedder).__name__
        result["dim"] = int(getattr(embedder, "dim", 256))

        # Single text encode (with rate limit retry)
        t0 = time.perf_counter()
        vec = embedder.embed("OMEGA benchmark test — hardware baseline measurement")
        single_ms = (time.perf_counter() - t0) * 1000
        result["single_embed_ms"] = round(single_ms, 1)
        result["vector_dim"] = len(vec) if vec else 0

        # Batch encode (3 texts — stay under Voyage 3 RPM free limit)
        time.sleep(1)  # Rate limit spacing
        texts = [f"Benchmark tekst {i} voor OMEGA" for i in range(3)]
        latencies = []
        for t in texts:
            time.sleep(0.5)  # 500ms spacing to avoid RPM limit
            t0 = time.perf_counter()
            embedder.embed(t)
            ms = (time.perf_counter() - t0) * 1000
            latencies.append(ms)
        batch_ms = sum(latencies)
        per_text_ms = batch_ms / len(latencies)
        result["batch_3_ms"] = round(batch_ms, 1)
        result["per_text_ms"] = round(per_text_ms, 1)

        _result("Provider", str(result["provider"]))
        _result("Dimension", f"{result['vector_dim']}d")
        _result("Single Embed", f"{single_ms:.1f}", "ms", single_ms < 500)
        _result("Batch 3", f"{batch_ms:.1f}", "ms")
        _result("Per Text", f"{per_text_ms:.1f}", "ms/text")

    except Exception as e:
        result["error"] = str(e)
        _result("Embedding", f"FOUT: {e}", ok=False)

    return result


async def bench_llm() -> dict:
    """5. LLM latency — Groq API probe."""
    _header("5. LLM LATENCY (GROQ)")

    result = {"available": False}

    try:
        from danny_toolkit.core.key_manager import get_key_manager
        km = get_key_manager()
        client = km.create_async_client("Benchmark")

        if not client:
            _result("Groq Client", "GEEN KEY BESCHIKBAAR", ok=False)
            return result

        from danny_toolkit.core.config import Config

        # Warm-up call
        t0 = time.perf_counter()
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=[{"role": "user", "content": "1+1="}],
                max_tokens=5,
                temperature=0,
            ),
            timeout=15,
        )
        warmup_ms = (time.perf_counter() - t0) * 1000

        # Real measurement (3 calls, average)
        latencies = []
        for i in range(3):
            t0 = time.perf_counter()
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model=Config.LLM_MODEL,
                    messages=[{"role": "user", "content": f"Wat is {i+2}+{i+2}?"}],
                    max_tokens=5,
                    temperature=0,
                ),
                timeout=15,
            )
            ms = (time.perf_counter() - t0) * 1000
            latencies.append(ms)

        avg_ms = sum(latencies) / len(latencies)
        min_ms = min(latencies)
        max_ms = max(latencies)

        result = {
            "available": True,
            "model": Config.LLM_MODEL,
            "warmup_ms": round(warmup_ms, 1),
            "avg_ms": round(avg_ms, 1),
            "min_ms": round(min_ms, 1),
            "max_ms": round(max_ms, 1),
            "calls": 3,
        }

        _result("Model", Config.LLM_MODEL)
        _result("Warmup", f"{warmup_ms:.1f}", "ms")
        _result("Avg Latency (3x)", f"{avg_ms:.1f}", "ms", avg_ms < 2000)
        _result("Min / Max", f"{min_ms:.1f} / {max_ms:.1f}", "ms")

    except Exception as e:
        result["error"] = str(e)
        _result("Groq", f"FOUT: {e}", ok=False)

    return result


async def bench_l1_pulse() -> dict:
    """6. L1 Pulse — FastAPI health endpoint."""
    _header("6. L1 PULSE (/api/v1/health)")

    result = {"available": False}

    try:
        import httpx
        api_key = os.getenv("OMEGA_API_KEY", "omega-dev-key")

        async with httpx.AsyncClient() as client:
            # Warmup
            await client.get(
                "http://127.0.0.1:8000/api/v1/health",
                headers={"X-API-Key": api_key},
                timeout=5,
            )

            # 10 measurements
            latencies = []
            for _ in range(10):
                t0 = time.perf_counter()
                resp = await client.get(
                    "http://127.0.0.1:8000/api/v1/health",
                    headers={"X-API-Key": api_key},
                    timeout=5,
                )
                ms = (time.perf_counter() - t0) * 1000
                latencies.append(ms)

            avg_ms = sum(latencies) / len(latencies)
            min_ms = min(latencies)
            max_ms = max(latencies)
            p95_ms = sorted(latencies)[int(len(latencies) * 0.95)]

            result = {
                "available": True,
                "avg_ms": round(avg_ms, 2),
                "min_ms": round(min_ms, 2),
                "max_ms": round(max_ms, 2),
                "p95_ms": round(p95_ms, 2),
                "calls": 10,
            }

            _result("Avg (10x)", f"{avg_ms:.2f}", "ms", avg_ms < 10)
            _result("Min / Max", f"{min_ms:.2f} / {max_ms:.2f}", "ms")
            _result("P95", f"{p95_ms:.2f}", "ms", p95_ms < 10)

    except Exception as e:
        result["error"] = str(e)
        _result("L1 Pulse", f"Server niet bereikbaar: {e}", ok=False)

    return result


async def bench_l3_deep() -> dict:
    """7. L3 Deep Scan — FastAPI deep health endpoint."""
    _header("7. L3 DEEP SCAN (/api/v1/health/deep)")

    result = {"available": False}

    try:
        import httpx
        api_key = os.getenv("OMEGA_API_KEY", "omega-dev-key")

        async with httpx.AsyncClient() as client:
            t0 = time.perf_counter()
            resp = await client.get(
                "http://127.0.0.1:8000/api/v1/health/deep",
                headers={"X-API-Key": api_key},
                timeout=30,
            )
            ms = (time.perf_counter() - t0) * 1000

            data = resp.json() if resp.status_code == 200 else {}

            result = {
                "available": resp.status_code == 200,
                "latency_ms": round(ms, 1),
                "status_code": resp.status_code,
                "groq_reachable": data.get("groq_reachable", False),
                "active_agents": data.get("active_agents", 0),
                "memory_mb": data.get("memory_mb", 0),
            }

            _result("Latency", f"{ms:.1f}", "ms", ms < 1000)
            _result("Status", f"{resp.status_code}")
            _result("Groq Reachable", str(data.get("groq_reachable", "?")))
            _result("Active Agents", str(data.get("active_agents", "?")))
            _result("Memory", f"{data.get('memory_mb', 0):.1f}", "MB")

    except Exception as e:
        result["error"] = str(e)
        _result("L3 Deep", f"Server niet bereikbaar: {e}", ok=False)

    return result


def bench_vector_store() -> dict:
    """8. VectorStore (ChromaDB + JSON) search performance."""
    _header("8. VECTOR STORE / RAG SEARCH")

    result = {"available": False}

    # --- A: ChromaDB (hoofd-RAG, 462+ docs) ---
    chroma_count = 0
    try:
        import chromadb
        chroma_path = DATA_DIR / "rag" / "chromadb"
        if chroma_path.exists():
            client = chromadb.PersistentClient(path=str(chroma_path))
            collections = client.list_collections()
            for col in collections:
                c = client.get_collection(col.name) if hasattr(col, 'name') else col
                name = c.name if hasattr(c, 'name') else str(c)
                cnt = c.count() if hasattr(c, 'count') else 0
                chroma_count += cnt
            result["chromadb_collections"] = len(collections)
            result["chromadb_docs"] = chroma_count

            # Search benchmark via ChromaDB
            if chroma_count > 0:
                # Use first collection with docs
                for col in collections:
                    c = client.get_collection(col.name) if hasattr(col, 'name') else col
                    if hasattr(c, 'count') and c.count() > 0:
                        queries = [
                            "SwarmEngine agent routing",
                            "CorticalStack memory events",
                            "GPU VRAM management",
                            "NeuralBus pub/sub events",
                            "Hallucination Shield verificatie",
                        ]
                        # ChromaDB needs embedding function — use query text search
                        try:
                            latencies = []
                            for q in queries:
                                t0 = time.perf_counter()
                                c.query(query_texts=[q], n_results=5)
                                ms = (time.perf_counter() - t0) * 1000
                                latencies.append(ms)
                            result["chromadb_avg_search_ms"] = round(sum(latencies) / len(latencies), 1)
                            result["chromadb_min_search_ms"] = round(min(latencies), 1)
                            result["chromadb_max_search_ms"] = round(max(latencies), 1)
                        except Exception as ce:
                            result["chromadb_search_error"] = str(ce)[:100]
                        break
    except Exception as e:
        result["chromadb_error"] = str(e)[:100]

    # --- B: JSON VectorStore (unified_vectors — 225 docs) ---
    json_count = 0
    json_path = DATA_DIR / "brain_memory" / "unified_vectors.json"
    try:
        if json_path.exists():
            import json as _json
            with open(json_path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            json_count = len(data.get("documenten", []))
            result["json_store_docs"] = json_count
            result["json_store_path"] = str(json_path.name)
    except Exception as e:
        result["json_store_error"] = str(e)[:100]

    total_docs = chroma_count + json_count
    result["total_docs"] = total_docs
    result["available"] = total_docs > 0

    _result("ChromaDB Docs", f"{chroma_count:,}")
    _result("JSON Store Docs", f"{json_count:,}")
    _result("Total RAG Docs", f"{total_docs:,}")

    if "chromadb_avg_search_ms" in result:
        _result("ChromaDB Search Avg (5x)", f"{result['chromadb_avg_search_ms']:.1f}", "ms", result["chromadb_avg_search_ms"] < 200)
        _result("ChromaDB Min / Max", f"{result['chromadb_min_search_ms']:.1f} / {result['chromadb_max_search_ms']:.1f}", "ms")
    elif "chromadb_search_error" in result:
        _result("ChromaDB Search", result["chromadb_search_error"][:60], ok=False)

    return result


# ==================== MAIN ====================

async def run_all_benchmarks() -> dict:
    """Run alle benchmarks en sla resultaten op."""
    start = time.perf_counter()

    print(f"\n{C}{'#'*60}")
    print(f"#  OMEGA HARDWARE BENCHMARK v1.0")
    print(f"#  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}{RESET}")

    results = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "system": "OMEGA v6.11.0",
    }

    # Sync benchmarks
    results["cpu_ram"] = bench_cpu_ram()
    results["gpu"] = bench_gpu()
    results["sqlite"] = bench_sqlite()
    results["embedding"] = bench_embedding()
    results["vector_store"] = bench_vector_store()

    # Async benchmarks
    results["llm"] = await bench_llm()
    results["l1_pulse"] = await bench_l1_pulse()
    results["l3_deep"] = await bench_l3_deep()

    total_s = time.perf_counter() - start
    results["total_benchmark_seconds"] = round(total_s, 1)

    # Summary
    _header("BENCHMARK SAMENVATTING")
    print(f"  {W}Totale benchmark tijd: {total_s:.1f}s{RESET}")
    print(f"  {W}Componenten getest: 8{RESET}")

    ok_count = sum(1 for k in ["cpu_ram", "gpu", "sqlite", "embedding", "vector_store", "llm", "l1_pulse", "l3_deep"]
                   if results.get(k, {}).get("available", True) and "error" not in results.get(k, {}))
    fail_count = 8 - ok_count
    color = G if fail_count == 0 else Y if fail_count <= 2 else R
    print(f"  {color}Geslaagd: {ok_count}/8 | Gefaald: {fail_count}/8{RESET}")

    # Save
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n  {G}Resultaten opgeslagen: {RESULTS_PATH}{RESET}")

    return results


if __name__ == "__main__":
    asyncio.run(run_all_benchmarks())
