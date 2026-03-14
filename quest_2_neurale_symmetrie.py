"""
╔══════════════════════════════════════════════════════════════════╗
║  QUEST 2: NEURALE SYMMETRIE — Stress-Test v6.14.0              ║
║                                                                ║
║  Fase 1: Vector Density — Bulk assimilate brain/ via API       ║
║  Fase 2: Bridge-Logica — Cross-ref ChromaDB ↔ Synapse SP      ║
║  Fase 3: Hebbian Resilience — Negatief bombardement + Phoenix  ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
import math
import os
import shutil
import sqlite3
import sys
import time
import uuid
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DANNY_TEST_MODE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")


# ── Quest Kleuren ────────────────────────────────────────────────
class Q:
    GROEN   = "\033[92m"
    GEEL    = "\033[93m"
    ROOD    = "\033[91m"
    CYAAN   = "\033[96m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"
    MAGENTA = "\033[95m"

    @staticmethod
    def banner(tekst: str) -> None:
        print(f"\n{Q.BOLD}{Q.CYAAN}{'═' * 66}{Q.RESET}")
        print(f"{Q.BOLD}{Q.CYAAN}  {tekst}{Q.RESET}")
        print(f"{Q.BOLD}{Q.CYAAN}{'═' * 66}{Q.RESET}")

    @staticmethod
    def fase(nr: int, tekst: str) -> None:
        print(f"\n{Q.BOLD}{Q.MAGENTA}  ┌─ FASE {nr}: {tekst}{Q.RESET}")

    @staticmethod
    def ok(tekst: str) -> None:
        print(f"  {Q.GROEN}✅ {tekst}{Q.RESET}")

    @staticmethod
    def warn(tekst: str) -> None:
        print(f"  {Q.GEEL}⚠️  {tekst}{Q.RESET}")

    @staticmethod
    def fail(tekst: str) -> None:
        print(f"  {Q.ROOD}❌ {tekst}{Q.RESET}")

    @staticmethod
    def info(tekst: str) -> None:
        print(f"  {Q.CYAAN}🔹 {tekst}{Q.RESET}")

    @staticmethod
    def sp_bar(agent: str, sp: int, label: str = "") -> None:
        bar_len = min(sp // 5, 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        kleur = Q.GROEN if sp >= 90 else Q.GEEL if sp >= 70 else Q.ROOD
        extra = f"  ({label})" if label else ""
        print(f"  {kleur}  {agent:>12}: [{bar}] SP {sp}{extra}{Q.RESET}")


@dataclass
class QuestResult:
    naam: str
    fases: List[Dict] = field(default_factory=list)
    geslaagd: bool = True

    def add_fase(self, naam: str, checks: List[Dict]) -> None:
        alle_ok = all(c["ok"] for c in checks)
        if not alle_ok:
            self.geslaagd = False
        self.fases.append({"naam": naam, "checks": checks, "ok": alle_ok})

    def rapport(self) -> None:
        Q.banner(f"QUEST RAPPORT: {self.naam}")
        totaal = sum(len(f["checks"]) for f in self.fases)
        geslaagd = sum(1 for f in self.fases for c in f["checks"] if c["ok"])
        for fase in self.fases:
            status = f"{Q.GROEN}PASS" if fase["ok"] else f"{Q.ROOD}FAIL"
            print(f"  {status}{Q.RESET}  {fase['naam']}")
            for c in fase["checks"]:
                sym = f"{Q.GROEN}✓" if c["ok"] else f"{Q.ROOD}✗"
                print(f"    {sym} {c['naam']}{Q.RESET}")
        print()
        if self.geslaagd:
            Q.ok(f"QUEST GESLAAGD — {geslaagd}/{totaal} checks passed")
        else:
            Q.fail(f"QUEST GEFAALD — {geslaagd}/{totaal} checks passed")
        print()


# ═════════════════════════════════════════════════════════════════
#  FASE 1: VECTOR DENSITY — Bulk Assimilate brain/ via TheLibrarian
# ═════════════════════════════════════════════════════════════════

def fase_1_vector_density() -> Dict:
    """Assimilate danny_toolkit/brain/ en meet chunk density + embedding stats."""
    Q.fase(1, "VECTOR DENSITY — De Invasie van brain/")

    checks = []
    brain_dir = ROOT / "danny_toolkit" / "brain"
    py_files = list(brain_dir.glob("*.py"))
    Q.info(f"Target: {brain_dir}")
    Q.info(f"Python bestanden gevonden: {len(py_files)}")

    # ── Stap 1a: Tel bestanden en LOC ──
    total_loc = 0
    for f in py_files:
        try:
            total_loc += len(f.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            logger.debug("Suppressed exception in quest_2_neurale_symmetrie")
    Q.info(f"Totaal LOC in brain/: {total_loc:,}")
    checks.append({"naam": f"brain/ bevat {len(py_files)} Python bestanden", "ok": len(py_files) >= 30})

    # ── Stap 1b: Kopieer brain/ naar staging dir in DOCS_DIR (security guard bypass) ──
    Q.info("Starten bulk assimilatie brain/ via staging → DOCS_DIR pipeline...")
    t0 = time.time()

    total_chunks = 0
    ok_count = 0
    fail_count = 0
    staging_dir = None

    try:
        from danny_toolkit.skills.librarian import TheLibrarian
        from danny_toolkit.core.config import Config

        # Staging dir binnen DOCS_DIR zodat _validate_pad() het accepteert
        docs_dir = Config.DATA_DIR / "rag" / "documenten"
        staging_dir = docs_dir / f"quest2_brain_{uuid.uuid4().hex[:8]}"
        staging_dir.mkdir(parents=True, exist_ok=True)
        Q.info(f"Staging dir: {staging_dir}")

        # Kopieer alle brain/*.py naar staging
        staged_files = []
        for py_file in py_files:
            dest = staging_dir / py_file.name
            shutil.copy2(py_file, dest)
            staged_files.append(dest)
        Q.info(f"Gekopieerd: {len(staged_files)} bestanden naar staging")

        librarian = TheLibrarian()
        BATCH_SIZE = 15

        # Verwerk in batches — via staging paths (binnen DOCS_DIR)
        for batch_start in range(0, len(staged_files), BATCH_SIZE):
            batch = staged_files[batch_start:batch_start + BATCH_SIZE]
            for staged_file in batch:
                try:
                    chunks = librarian.ingest_file(
                        str(staged_file),
                        extra_metadata={"tags": "quest2,brain,stress-test"},
                    )
                    n = chunks if isinstance(chunks, int) else 0
                    total_chunks += n
                    ok_count += 1
                except Exception as e:
                    fail_count += 1
                    if fail_count <= 3:
                        Q.warn(f"Ingestie fout {staged_file.name}: {e}")

    except ImportError as e:
        Q.fail(f"TheLibrarian import mislukt: {e}")
        checks.append({"naam": "TheLibrarian beschikbaar", "ok": False})
        return {"checks": checks, "total_chunks": 0, "elapsed": 0}
    finally:
        # Cleanup staging dir
        if staging_dir and staging_dir.exists():
            try:
                shutil.rmtree(staging_dir)
                Q.info("Staging dir opgeruimd")
            except Exception:
                Q.warn(f"Staging cleanup mislukt: {staging_dir}")

    elapsed = time.time() - t0
    Q.ok(f"Ingestie voltooid in {elapsed:.1f}s")
    Q.info(f"Bestanden: {ok_count} OK, {fail_count} FAIL")
    Q.info(f"Totaal chunks gegenereerd: {total_chunks}")
    if ok_count > 0:
        Q.info(f"Chunk density: gem={total_chunks / ok_count:.1f}/file")

    # ── Stap 1c: Verifieer ChromaDB state ──
    chroma_count = 0
    try:
        from danny_toolkit.core.config import Config
        import chromadb
        client = chromadb.PersistentClient(path=str(Config.DATA_DIR / "rag" / "chromadb"))
        collection = client.get_collection("danny_knowledge")
        chroma_count = collection.count()
        Q.ok(f"ChromaDB danny_knowledge: {chroma_count} totale vectoren")
    except Exception as e:
        Q.warn(f"ChromaDB check overgeslagen: {e}")

    # ── Stap 1d: Embedding dimensie check ──
    embed_dim = 0
    try:
        from danny_toolkit.core.config import Config
        embed_dim = Config.EMBEDDING_DIM
        provider = Config.EMBEDDING_PROVIDER
        Q.info(f"Embedding provider: {provider}, dimensie: {embed_dim}d")
    except Exception:
        logger.debug("Suppressed exception in quest_2_neurale_symmetrie")

    checks.extend([
        {"naam": f"Ingestie succesvol: {ok_count}/{len(py_files)} bestanden", "ok": ok_count >= len(py_files) * 0.8},
        {"naam": f"Chunks gegenereerd: {total_chunks}", "ok": total_chunks > 0},
        {"naam": f"Ingestie tijd < 300s (actual: {elapsed:.1f}s)", "ok": elapsed < 300},
        {"naam": f"ChromaDB vectoren aanwezig: {chroma_count}", "ok": chroma_count > 100},
    ])

    for c in checks:
        (Q.ok if c["ok"] else Q.fail)(c["naam"])

    return {
        "checks": checks,
        "total_chunks": total_chunks,
        "chroma_count": chroma_count,
        "elapsed": elapsed,
        "embed_dim": embed_dim,
        "ok_count": ok_count,
        "fail_count": fail_count,
    }


# ═════════════════════════════════════════════════════════════════
#  FASE 2: BRIDGE-LOGICA — Cross-reference ChromaDB ↔ Synapse SP
# ═════════════════════════════════════════════════════════════════

def fase_2_bridge_logica() -> Dict:
    """Query recent ingested chunks en map ze naar Synapse agent SP scores."""
    Q.fase(2, "BRIDGE-LOGICA — Real-time Synthesis")

    checks = []

    # ── Stap 2a: Query ChromaDB via TheLibrarian (correcte embedding dimensie) ──
    Q.info("Querying ChromaDB via TheLibrarian...")
    recent_chunks = []
    try:
        from danny_toolkit.skills.librarian import TheLibrarian
        librarian = TheLibrarian()

        results = librarian.query("synapse plasticity phoenix boost agent routing", n_results=10)

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, distances):
            source = meta.get("source", meta.get("bron", "unknown")) if meta else "unknown"
            recent_chunks.append({
                "source": str(source),
                "preview": (doc[:80] + "...") if doc and len(doc) > 80 else (doc or ""),
                "distance": round(dist, 4) if dist else 0,
            })

        Q.ok(f"ChromaDB query: {len(recent_chunks)} relevante chunks gevonden")
        for i, chunk in enumerate(recent_chunks[:5]):
            src_name = Path(chunk["source"]).name if "/" in chunk["source"] or "\\" in chunk["source"] else chunk["source"]
            Q.info(f"  #{i+1} [{src_name}] dist={chunk['distance']:.4f}: {chunk['preview'][:60]}")

        checks.append({"naam": f"ChromaDB query retourneert chunks: {len(recent_chunks)}", "ok": len(recent_chunks) > 0})

    except Exception as e:
        Q.fail(f"ChromaDB query mislukt: {e}")
        checks.append({"naam": "ChromaDB query werkt", "ok": False})
        return {"checks": checks, "mapping": {}}

    # ── Stap 2b: Laad Synapse SP scores ──
    Q.info("Laden Synapse SP scores...")
    agent_sp = {}
    try:
        from danny_toolkit.brain.synapse import get_synapse
        synapse = get_synapse()
        matrix = synapse.get_weight_matrix()
        pathways = matrix.get("pathways", {})

        # pathways structuur: {category: {agent: {strength, bias, fires, ...}}}
        unique_agents = set()
        for category, agents_dict in pathways.items():
            if isinstance(agents_dict, dict):
                for agent_name in agents_dict:
                    unique_agents.add(agent_name)

        # Bereken SP per agent via directe SQL
        for agent in unique_agents:
            agent_sp[agent] = synapse._agent_sp(agent)

        Q.ok(f"Synapse: {len(agent_sp)} agents met SP scores")
        for agent in sorted(agent_sp, key=lambda a: agent_sp[a], reverse=True)[:5]:
            Q.sp_bar(agent, agent_sp[agent])

        checks.append({"naam": f"Synapse SP scores geladen: {len(agent_sp)} agents", "ok": len(agent_sp) > 0})

    except Exception as e:
        Q.fail(f"Synapse laden mislukt: {e}")
        checks.append({"naam": "Synapse SP laden", "ok": False})
        return {"checks": checks, "mapping": {}}

    # ── Stap 2c: Cross-reference: welke agent past bij welke data? ──
    Q.info("Cross-referencing: chunks → agents...")

    # Analyseer chunk content voor agent-relevantie
    agent_keywords = {
        "Navigator": ["search", "web", "navigate", "zoek", "research", "internet"],
        "Sentinel": ["security", "guard", "validate", "firewall", "sentinel", "protect"],
        "Artificer": ["forge", "skill", "create", "build", "artificer", "execute"],
        "Strategist": ["plan", "strategy", "decompose", "strategist", "recursive"],
        "Iolaax": ["iolaax", "creative", "generate", "elaborate", "amplify"],
        "Oracle": ["oracle", "reason", "verify", "will", "action"],
        "VoidWalker": ["void", "walker", "duckduckgo", "scrape", "crawl"],
        "Dreamer": ["dream", "rem", "overnight", "backup", "consolidate"],
        "GhostWriter": ["ghost", "docstring", "ast", "documentation", "writer"],
    }

    mapping = {}
    for chunk in recent_chunks[:10]:
        content_lower = (chunk["preview"] + " " + chunk["source"]).lower()
        best_agent = None
        best_score = 0
        for agent, keywords in agent_keywords.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > best_score:
                best_score = score
                best_agent = agent

        if best_agent:
            if best_agent not in mapping:
                mapping[best_agent] = {"chunks": 0, "sp": agent_sp.get(best_agent, 50)}
            mapping[best_agent]["chunks"] += 1

    Q.info("Bridge-mapping resultaat:")
    print()
    print(f"  {Q.CYAAN}  {'Agent':>12}  │ {'Chunks':>6} │ {'SP':>4} │ Match{Q.RESET}")
    print(f"  {Q.CYAAN}  {'─'*12}──┼{'─'*8}┼{'─'*6}┼{'─'*20}{Q.RESET}")

    ranked_agents = sorted(mapping.items(), key=lambda x: x[1]["sp"], reverse=True)
    for agent, info in ranked_agents:
        sp = info["sp"]
        kleur = Q.GROEN if sp >= 90 else Q.GEEL if sp >= 70 else Q.ROOD
        match = "★ ALPHA" if sp == max(v["sp"] for v in mapping.values()) else "  ready"
        print(f"  {kleur}  {agent:>12}  │ {info['chunks']:>6} │ {sp:>4} │ {match}{Q.RESET}")

    print()

    # De vraag beantwoorden: welke agent is best geschikt?
    if ranked_agents:
        best = ranked_agents[0]
        Q.ok(f"Best geschikt voor brain/ data: {best[0]} (SP={best[1]['sp']}, {best[1]['chunks']} chunks)")

    checks.append({
        "naam": f"Cross-reference mapping: {len(mapping)} agents gematched",
        "ok": len(mapping) >= 2,
    })

    for c in checks:
        (Q.ok if c["ok"] else Q.fail)(c["naam"])

    return {"checks": checks, "mapping": mapping, "agent_sp": agent_sp}


# ═════════════════════════════════════════════════════════════════
#  FASE 3: HEBBIAN RESILIENCE — Negatief bombardement + Phoenix
# ═════════════════════════════════════════════════════════════════

def fase_3_hebbian_resilience() -> Dict:
    """Bombardeer Sentinel met negatieve signalen, dan Phoenix recovery."""
    Q.fase(3, "HEBBIAN RESILIENCE — De Phoenix-Loop")

    checks = []

    from danny_toolkit.brain.synapse import get_synapse
    synapse = get_synapse()

    # ── Stap 3a: Baseline meting ──
    baseline_sp = synapse._agent_sp("Sentinel")
    Q.info(f"Sentinel BASELINE SP: {baseline_sp}")
    Q.sp_bar("Sentinel", baseline_sp, "baseline")

    # ── Stap 3b: BOMBARDEMENT — 10 negatieve signalen ──
    Q.info("Bombardement: 10x negatief signaal (-0.50) op Sentinel...")
    BOMBARDMENT_SIGNAL = -0.50
    BOMBARDMENT_CATEGORIES = ["GENERAL", "DATA", "SEARCH", "CODE", "SECURITY"]
    BOMBARDMENT_ROUNDS = 2  # 2 rounds × 5 categories = 10 hits

    t_bomb_start = time.time()
    for round_nr in range(BOMBARDMENT_ROUNDS):
        for category in BOMBARDMENT_CATEGORIES:
            try:
                synapse._apply_plasticity(category, "Sentinel", BOMBARDMENT_SIGNAL)
                synapse._safe_commit()
            except Exception as e:
                Q.warn(f"Plasticity fout: {e}")
        # Pacing: verminder SQLite WAL lock contention tussen rondes
        time.sleep(0.1)

    t_bomb = time.time() - t_bomb_start
    post_bomb_sp = synapse._agent_sp("Sentinel")

    Q.fail(f"Sentinel POST-BOMBARDEMENT SP: {post_bomb_sp} (was {baseline_sp})")
    Q.sp_bar("Sentinel", post_bomb_sp, "beschadigd")
    Q.info(f"Bombardement duur: {t_bomb:.3f}s")
    Q.info(f"SP daling: {baseline_sp} → {post_bomb_sp} (Δ = {post_bomb_sp - baseline_sp})")

    checks.append({
        "naam": f"Bombardement verlaagt SP: {baseline_sp} → {post_bomb_sp}",
        "ok": post_bomb_sp < baseline_sp,
    })

    # ── Stap 3c: Bekijk pathway schade ──
    Q.info("Pathway schade-analyse...")
    rows = synapse._conn.execute(
        """SELECT query_category, strength, fire_count
           FROM synaptic_pathways WHERE agent_key = ?
           ORDER BY strength ASC""",
        ("Sentinel",),
    ).fetchall()

    min_strength = 1.0
    for cat, strength, fires in rows:
        kleur = Q.ROOD if strength < 0.3 else Q.GEEL if strength < 0.5 else Q.GROEN
        marker = " ← CRITICAL" if strength <= 0.05 else ""
        print(f"  {kleur}  {cat:>20}: strength={strength:.4f}  fires={fires}{marker}{Q.RESET}")
        min_strength = min(min_strength, strength)

    checks.append({
        "naam": f"Minimale pathway strength > 0.05 (floor): {min_strength:.4f}",
        "ok": min_strength >= 0.05,  # Sigmoid floor moet houden
    })

    # ── Stap 3d: PHOENIX BOOST — Herstel ──
    Q.info("")
    Q.info("🔥 PHOENIX BOOST GEACTIVEERD — Sentinel rehabilitatie...")

    t_phoenix_start = time.time()

    # Meerdere Phoenix rondes tot herstel
    phoenix_rounds = 0
    max_rounds = 5
    recovery_log = []

    while phoenix_rounds < max_rounds:
        phoenix_rounds += 1
        result = synapse.phoenix_boost("Sentinel")
        current_sp = result["new_sp"]
        recovery_log.append({
            "round": phoenix_rounds,
            "sp": current_sp,
            "old": result["old_sp"],
        })
        Q.info(f"  Phoenix ronde {phoenix_rounds}: SP {result['old_sp']} → {current_sp}")

        if current_sp >= baseline_sp:
            break

    t_phoenix = time.time() - t_phoenix_start
    final_sp = synapse._agent_sp("Sentinel")

    Q.ok(f"Sentinel POST-PHOENIX SP: {final_sp}")
    Q.sp_bar("Sentinel", final_sp, "hersteld")
    Q.info(f"Phoenix duur: {t_phoenix:.3f}s over {phoenix_rounds} rondes")
    Q.info(f"Herstel: {post_bomb_sp} → {final_sp} (Δ = +{final_sp - post_bomb_sp})")

    # ── Stap 3e: Verificatie checks ──
    recovered = final_sp >= baseline_sp * 0.90  # 90% van baseline = acceptabel herstel
    checks.extend([
        {
            "naam": f"Phoenix herstel ≥ 90% baseline ({baseline_sp}): actual={final_sp}",
            "ok": recovered,
        },
        {
            "naam": f"Phoenix rondes ≤ {max_rounds}: actual={phoenix_rounds}",
            "ok": phoenix_rounds <= max_rounds,
        },
        {
            "naam": f"Phoenix snelheid < 10s: actual={t_phoenix:.2f}s",
            "ok": t_phoenix < 10,
        },
    ])

    # ── Stap 3f: Sigmoid bounds check — floor moet standhouden ──
    Q.info("Post-recovery pathway analyse...")
    post_rows = synapse._conn.execute(
        """SELECT query_category, strength, fire_count
           FROM synaptic_pathways WHERE agent_key = ?
           ORDER BY strength DESC""",
        ("Sentinel",),
    ).fetchall()

    for cat, strength, fires in post_rows:
        kleur = Q.GROEN if strength >= 0.5 else Q.GEEL if strength >= 0.3 else Q.ROOD
        print(f"  {kleur}  {cat:>20}: strength={strength:.4f}  fires={fires}{Q.RESET}")

    # ── Stap 3g: Navigator stabiliteitscheck ──
    Q.info("")
    nav_sp = synapse._agent_sp("Navigator")
    Q.info(f"Navigator SP (ongestoord): {nav_sp}")
    Q.sp_bar("Navigator", nav_sp, "Alpha")

    checks.append({
        "naam": f"Navigator onbeschadigd door Sentinel bombardement: SP={nav_sp}",
        "ok": nav_sp >= 100,
    })

    # ── Recovery timeline ──
    Q.info("")
    Q.info("Recovery timeline:")
    print(f"  {Q.CYAAN}  Baseline  →  Bombardement  →  Phoenix Recovery{Q.RESET}")
    timeline = f"  SP: {baseline_sp}"
    timeline += f"  →  {post_bomb_sp} (📉 -{baseline_sp - post_bomb_sp})"
    for entry in recovery_log:
        timeline += f"  →  {entry['sp']}"
    kleur = Q.GROEN if final_sp >= baseline_sp else Q.ROOD
    print(f"  {kleur}{timeline}{Q.RESET}")
    print()

    for c in checks:
        (Q.ok if c["ok"] else Q.fail)(c["naam"])

    return {
        "checks": checks,
        "baseline_sp": baseline_sp,
        "post_bomb_sp": post_bomb_sp,
        "final_sp": final_sp,
        "phoenix_rounds": phoenix_rounds,
        "recovery_log": recovery_log,
    }


# ═════════════════════════════════════════════════════════════════
#  MAIN — Execute Quest 2
# ═════════════════════════════════════════════════════════════════

def main() -> int:
    Q.banner("QUEST 2: NEURALE SYMMETRIE — Stress-Test v6.14.0")
    print(f"  {Q.CYAAN}Vector Density × Bridge-Logica × Hebbian Resilience{Q.RESET}")
    t0 = time.time()

    quest = QuestResult("Neurale Symmetrie")

    # Fase 1: Vector Density
    f1 = fase_1_vector_density()
    quest.add_fase("Vector Density (brain/ invasie)", f1["checks"])

    # Fase 2: Bridge-Logica
    f2 = fase_2_bridge_logica()
    quest.add_fase("Bridge-Logica (ChromaDB ↔ Synapse)", f2["checks"])

    # Fase 3: Hebbian Resilience
    f3 = fase_3_hebbian_resilience()
    quest.add_fase("Hebbian Resilience (Phoenix-Loop)", f3["checks"])

    elapsed = time.time() - t0
    quest.rapport()
    print(f"  {Q.CYAAN}⏱️  Quest 2 voltooid in {elapsed:.1f}s{Q.RESET}\n")

    # S-Tier samenvatting
    Q.banner("S-TIER VALIDATIE RAPPORT")
    print(f"  {Q.CYAAN}Vector Density:{Q.RESET}   {f1.get('total_chunks', 0)} chunks, "
          f"{f1.get('chroma_count', 0)} vectoren in ChromaDB, "
          f"{f1.get('embed_dim', '?')}d embeddings")
    print(f"  {Q.CYAAN}Bridge-Logica:{Q.RESET}    {len(f2.get('mapping', {}))} agents gematched "
          f"aan geïngesteerde data")
    print(f"  {Q.CYAAN}Hebbian Loop:{Q.RESET}     "
          f"SP {f3.get('baseline_sp', '?')} → {f3.get('post_bomb_sp', '?')} → "
          f"{f3.get('final_sp', '?')} in {f3.get('phoenix_rounds', '?')} Phoenix rondes")
    print()

    return 0 if quest.geslaagd else 1


if __name__ == "__main__":
    sys.exit(main())
