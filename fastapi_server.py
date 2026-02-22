"""
Danny Toolkit — FastAPI REST API Server.

Stelt de SwarmEngine beschikbaar via HTTP endpoints zodat
elke client (mobiel, web, Telegram) het systeem kan aanspreken.

Gebruik:
    python fastapi_server.py
    Of: danny-api  (als entry point)

Docs:
    http://localhost:8000/docs  (Swagger UI)
"""

import asyncio
import io
import json
import logging
import os
import sys
import time
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

try:
    from fastapi.staticfiles import StaticFiles
    from jinja2 import Environment, FileSystemLoader
    _WEB_DIR = Path(__file__).parent / "danny_toolkit" / "web"
    _templates = Environment(
        loader=FileSystemLoader(str(_WEB_DIR / "templates")),
        autoescape=True,
    )
    HAS_DASHBOARD = True
except ImportError:
    HAS_DASHBOARD = False
from pydantic import BaseModel, Field

import uvicorn

# Windows UTF-8 fix
if os.name == "nt":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# .env laden
load_dotenv(Path(__file__).parent / ".env")

# WARNING: Wijzig deze sleutel in productie! Standaard is onveilig.
FASTAPI_SECRET_KEY = os.getenv(
    "FASTAPI_SECRET_KEY",
    "verander-dit-naar-een-willekeurige-sleutel",
)
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", "8000"))

_SERVER_START_TIME = time.time()

# Startup validatie (Phase 26)
try:
    from danny_toolkit.core.startup_validator import valideer_opstart
    valideer_opstart()
except ImportError:
    pass

# ─── SINGLETON BRAIN ───────────────────────────────

_brain = None


def _get_brain():
    """Lazy-load PrometheusBrain (1x per worker)."""
    global _brain
    if _brain is None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            from danny_toolkit.brain.trinity_omega import (
                PrometheusBrain,
            )
            _brain = PrometheusBrain()
    return _brain


# ─── PYDANTIC MODELLEN ─────────────────────────────

class QueryRequest(BaseModel):
    """Inkomend verzoek voor de SwarmEngine."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Prompt voor de SwarmEngine",
    )
    stream: bool = Field(
        default=False,
        description="SSE streaming (true) of wachten (false)",
    )


class PayloadResponse(BaseModel):
    """Eén SwarmPayload als JSON."""
    agent: str
    type: str
    display_text: str
    timestamp: float
    metadata: Dict[str, Any] = {}


class QueryResponse(BaseModel):
    """Response van /api/v1/query."""
    payloads: List[PayloadResponse]
    execution_time: float


class HealthResponse(BaseModel):
    """Response van /api/v1/health."""
    status: str
    brain_online: bool
    governor_status: str
    circuit_breaker: str
    timestamp: str
    version: str
    uptime_seconds: float = 0.0
    memory_mb: float = 0.0
    active_agents: int = 0
    # Deep probes (Phase 25)
    groq_reachable: bool = False
    cortical_stack_writable: bool = False
    disk_free_gb: float = 0.0
    agents_in_cooldown: int = 0
    # Pipeline metrics (Phase 26)
    agent_metrics: Dict[str, Any] = {}
    response_cache: Dict[str, Any] = {}


class AgentInfo(BaseModel):
    """Informatie over één agent."""
    name: str
    role: str
    tier: str
    status: str
    energy: int
    tasks_completed: int


class HeartbeatResponse(BaseModel):
    """Response van /api/v1/heartbeat."""
    is_awake: bool
    pulse_count: int
    schedule: List[Dict[str, Any]]
    last_check: Dict[str, float]


class IngestResponse(BaseModel):
    """Response van /api/v1/ingest."""
    status: str
    bestand: str
    chunks: int


# ─── AUTH ───────────────────────────────────────────

async def verify_api_key(
    x_api_key: str = Header(
        ..., description="API sleutel voor authenticatie"
    ),
):
    """Controleer de API key via X-API-Key header."""
    if x_api_key != FASTAPI_SECRET_KEY:
        raise HTTPException(
            status_code=401,
            detail="Ongeldige API sleutel.",
        )
    return x_api_key


# ─── APP ────────────────────────────────────────────

app = FastAPI(
    title="Danny Toolkit API",
    description=(
        "REST API voor de Danny Toolkit SwarmEngine. "
        "Stuur berichten, bekijk agents en systeem status."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def _shutdown_event():
    """Flush CorticalStack bij server shutdown."""
    try:
        from danny_toolkit.brain.cortical_stack import (
            get_cortical_stack,
        )
        get_cortical_stack().flush()
    except Exception as e:
        logger.debug("CorticalStack flush on shutdown failed: %s", e)


# ─── ENDPOINTS ──────────────────────────────────────

@app.post(
    "/api/v1/query",
    response_model=QueryResponse,
    summary="Stuur een prompt naar de SwarmEngine",
    tags=["Swarm"],
)
async def query(
    req: QueryRequest,
    _key: str = Depends(verify_api_key),
):
    """Verwerk een prompt via de SwarmEngine en
    retourneer de resultaten als SwarmPayload lijst.
    """
    from swarm_engine import SwarmEngine

    brain = _get_brain()

    if req.stream:
        return await _stream_response(req.message, brain)

    start = time.time()
    engine = SwarmEngine(brain=brain)

    try:
        payloads = await engine.run(req.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SwarmEngine fout: {e}",
        )

    elapsed = round(time.time() - start, 2)

    return QueryResponse(
        payloads=[
            PayloadResponse(
                agent=p.agent,
                type=p.type,
                display_text=str(p.display_text),
                timestamp=p.timestamp,
                metadata=p.metadata
                if isinstance(p.metadata, dict)
                else {},
            )
            for p in payloads
        ],
        execution_time=elapsed,
    )


async def _stream_response(message: str, brain):
    """SSE streaming via async generator (fix: was sync wrapper)."""
    from swarm_engine import SwarmEngine

    async def _generate():
        engine = SwarmEngine(brain=brain)
        updates = []

        def callback(msg):
            updates.append(msg)

        try:
            payloads = await engine.run(
                message, callback
            )
        except Exception as e:
            yield (
                f"data: {json.dumps({'error': str(e)})}"
                "\n\n"
            )
            return

        for update in updates:
            yield (
                f"data: {json.dumps({'update': update})}"
                "\n\n"
            )

        for p in payloads:
            payload_data = {
                "agent": p.agent,
                "type": p.type,
                "display_text": str(p.display_text),
                "timestamp": p.timestamp,
                "metadata": p.metadata
                if isinstance(p.metadata, dict)
                else {},
            }
            yield (
                f"data: {json.dumps({'payload': payload_data})}"
                "\n\n"
            )

        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
    )


@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    summary="Systeem gezondheid opvragen",
    tags=["Systeem"],
)
async def health(
    _key: str = Depends(verify_api_key),
):
    """Retourneer de status van het systeem,
    inclusief Governor en circuit breaker.
    """
    brain = _get_brain()

    # Governor status ophalen
    gov_status = "ONBEKEND"
    cb_status = "ONBEKEND"
    try:
        gov = brain.governor
        gov_status = "ACTIEF"
        if hasattr(gov, "_api_failures"):
            failures = gov._api_failures
            if failures >= gov.MAX_API_FAILURES:
                cb_status = "OPEN"
            elif failures > 0:
                cb_status = "HALF_OPEN"
            else:
                cb_status = "CLOSED"
    except Exception as e:
        logger.debug("Governor status ophalen mislukt: %s", e)
        gov_status = "NIET BESCHIKBAAR"
        cb_status = "ONBEKEND"

    # Uptime
    uptime = time.time() - _SERVER_START_TIME

    # Memory usage
    mem_mb = 0.0
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        mem_mb = proc.memory_info().rss / (1024 * 1024)
    except Exception as e:
        logger.debug("Memory usage ophalen mislukt: %s", e)

    # Active agents
    actief = 0
    if hasattr(brain, "nodes"):
        actief = sum(
            1 for n in brain.nodes.values()
            if n.status == "ACTIVE"
        )

    # Deep probe: Groq reachable (1-token call, 10s timeout)
    groq_ok = False
    try:
        from danny_toolkit.core.key_manager import get_key_manager as _gkm
        _km = _gkm()
        _probe_client = _km.create_async_client("HealthProbe")
        if _probe_client:
            from danny_toolkit.core.config import Config as _ProbeCfg
            await asyncio.wait_for(
                _probe_client.chat.completions.create(
                    model=_ProbeCfg.LLM_FALLBACK_MODEL,
                    messages=[{"role": "user", "content": "ok"}],
                    max_tokens=1,
                ),
                timeout=10,
            )
            groq_ok = True
    except Exception as e:
        logger.debug("Groq health probe mislukt: %s", e)

    # Deep probe: CorticalStack writable
    stack_ok = False
    try:
        from danny_toolkit.brain.cortical_stack import (
            get_cortical_stack as _gcs,
        )
        _stack = _gcs()
        _stack.log_event(
            actor="health_probe",
            action="ping",
            source="fastapi",
        )
        _stack.flush()
        stack_ok = True
    except Exception as e:
        logger.debug("CorticalStack health probe mislukt: %s", e)

    # Deep probe: Disk free
    disk_free = 0.0
    try:
        import shutil as _shutil
        from danny_toolkit.core.config import Config as _DiskCfg
        usage = _shutil.disk_usage(str(_DiskCfg.DATA_DIR))
        disk_free = round(usage.free / (1024 ** 3), 2)
    except Exception as e:
        logger.debug("Disk usage probe mislukt: %s", e)

    # Deep probe: Agents in cooldown
    cooldown_count = 0
    try:
        from danny_toolkit.core.key_manager import get_key_manager as _gkm2
        _km2_status = _gkm2().get_status()
        cooldown_count = sum(
            1 for a in _km2_status.get("agents", {}).values()
            if a.get("in_cooldown", False)
        )
    except Exception as e:
        logger.debug("Cooldown probe mislukt: %s", e)

    # Pipeline metrics (Phase 26)
    cache_stats = {}
    try:
        from danny_toolkit.core.response_cache import get_response_cache
        cache_stats = get_response_cache().stats()
    except ImportError:
        pass

    agent_m = {}
    try:
        from swarm_engine import get_pipeline_metrics
        agent_m = get_pipeline_metrics()
    except ImportError:
        pass

    return HealthResponse(
        status="ONLINE",
        brain_online=brain.is_online,
        governor_status=gov_status,
        circuit_breaker=cb_status,
        timestamp=datetime.now().isoformat(),
        version="6.0.0",
        uptime_seconds=round(uptime, 1),
        memory_mb=round(mem_mb, 1),
        active_agents=actief,
        groq_reachable=groq_ok,
        cortical_stack_writable=stack_ok,
        disk_free_gb=disk_free,
        agents_in_cooldown=cooldown_count,
        agent_metrics=agent_m,
        response_cache=cache_stats,
    )


@app.get(
    "/api/v1/agents",
    response_model=List[AgentInfo],
    summary="Lijst van alle agents",
    tags=["Swarm"],
)
async def agents(
    _key: str = Depends(verify_api_key),
):
    """Retourneer alle beschikbare agents met hun
    status, energie en aantal voltooide taken.
    """
    brain = _get_brain()
    result = []

    if hasattr(brain, "nodes"):
        for role, node in brain.nodes.items():
            result.append(AgentInfo(
                name=node.name,
                role=role.value
                if hasattr(role, "value")
                else str(role),
                tier=node.tier.value
                if hasattr(node.tier, "value")
                else str(node.tier),
                status=node.status,
                energy=node.energy,
                tasks_completed=node.tasks_completed,
            ))

    return result


@app.post(
    "/api/v1/ingest",
    response_model=IngestResponse,
    summary="Document uploaden naar RAG",
    tags=["RAG"],
)
async def ingest(
    bestand: UploadFile = File(
        ..., description="Tekstbestand om te indexeren"
    ),
    _key: str = Depends(verify_api_key),
):
    """Upload een document en indexeer het via
    TheLibrarian naar ChromaDB.
    """
    # Valideer bestandstype
    if not bestand.filename:
        raise HTTPException(
            status_code=400,
            detail="Geen bestand ontvangen.",
        )

    allowed = {".txt", ".md", ".py", ".json", ".csv"}
    ext = Path(bestand.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Bestandstype '{ext}' niet toegestaan. "
                f"Gebruik: {', '.join(allowed)}"
            ),
        )

    # Sla op in RAG documenten map
    from danny_toolkit.core.config import Config
    Config.ensure_dirs()
    docs_dir = Config.RAG_DATA_DIR / "documenten"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Veilige bestandsnaam
    safe_name = (
        bestand.filename.replace("..", "")
        .replace("/", "_")
        .replace("\\", "_")
    )
    doel = docs_dir / safe_name

    inhoud = await bestand.read()
    doel.write_bytes(inhoud)

    # Probeer te indexeren via TheLibrarian
    chunks = 0
    try:
        from danny_toolkit.skills.librarian import (
            TheLibrarian,
        )
    except ImportError:
        chunks = -1

    if chunks == 0:
        try:
            librarian = TheLibrarian()
            chunks = librarian.ingest_file(str(doel))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Indexering mislukt: {e}",
            )

    return IngestResponse(
        status="OK" if chunks >= 0 else "OPGESLAGEN",
        bestand=safe_name,
        chunks=max(chunks, 0),
    )


@app.get(
    "/api/v1/heartbeat",
    response_model=HeartbeatResponse,
    summary="HeartbeatDaemon status",
    tags=["Systeem"],
)
async def heartbeat(
    _key: str = Depends(verify_api_key),
):
    """Retourneer de status van de HeartbeatDaemon
    (indien actief).
    """
    try:
        from daemon_heartbeat import HeartbeatDaemon
        # Maak een tijdelijke instantie voor schema info
        daemon = HeartbeatDaemon.__new__(
            HeartbeatDaemon
        )
        daemon.schedule = [
            {
                "name": "RAG Health Check",
                "interval": 120,
                "prompt": (
                    "Zoek in de documenten:"
                    " wat zijn de python"
                    " best practices?"
                ),
            },
            {
                "name": "System Heartbeat",
                "interval": 60,
                "prompt": "hallo",
            },
        ]
        return HeartbeatResponse(
            is_awake=False,
            pulse_count=0,
            schedule=daemon.schedule,
            last_check={},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"HeartbeatDaemon fout: {e}",
        )


# ─── WEB DASHBOARD (HTMX) ─────────────────────────

if HAS_DASHBOARD:
    app.mount(
        "/static",
        StaticFiles(directory=str(_WEB_DIR / "static")),
        name="static",
    )

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url="/ui/")

    @app.get("/ui/", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard():
        tmpl = _templates.get_template("dashboard.html")
        return HTMLResponse(tmpl.render())

    @app.get("/ui/partials/agents", response_class=HTMLResponse, include_in_schema=False)
    async def partial_agents():
        brain = _get_brain()
        agents = []
        if hasattr(brain, "nodes"):
            for role, node in brain.nodes.items():
                agents.append({
                    "name": node.name,
                    "status": node.status,
                    "tier": node.tier.value if hasattr(node.tier, "value") else str(node.tier),
                    "energy": node.energy,
                    "tasks_completed": node.tasks_completed,
                })
        tmpl = _templates.get_template("partials/agent_grid.html")
        return HTMLResponse(tmpl.render(agents=agents))

    @app.get("/ui/partials/governor", response_class=HTMLResponse, include_in_schema=False)
    async def partial_governor():
        brain = _get_brain()
        stats = {}
        try:
            gov = brain.governor
            stats["Status"] = "ACTIEF"
            if hasattr(gov, "_api_failures"):
                failures = gov._api_failures
                if failures >= gov.MAX_API_FAILURES:
                    stats["Circuit Breaker"] = "OPEN"
                elif failures > 0:
                    stats["Circuit Breaker"] = "HALF_OPEN"
                else:
                    stats["Circuit Breaker"] = "CLOSED"
                stats["Failures"] = failures
            if hasattr(gov, "_tokens_used_hour"):
                stats["Tokens/uur"] = gov._tokens_used_hour
            if hasattr(gov, "MAX_TOKENS_PER_HOUR"):
                stats["Max tokens/uur"] = gov.MAX_TOKENS_PER_HOUR
        except Exception:
            stats["Status"] = "NIET BESCHIKBAAR"
        tmpl = _templates.get_template("partials/governor.html")
        return HTMLResponse(tmpl.render(stats=stats))

    @app.get("/ui/partials/rate-limits", response_class=HTMLResponse, include_in_schema=False)
    async def partial_rate_limits():
        limits = []
        try:
            from danny_toolkit.core.key_manager import get_key_manager
            km = get_key_manager()
            if hasattr(km, "get_status"):
                status = km.get_status()
                for agent_name, info in status.items():
                    rpm_max = info.get("rpm_limit", 30)
                    tpm_max = info.get("tpm_limit", 6000)
                    rpm_used = info.get("rpm_used", 0)
                    tpm_used = info.get("tpm_used", 0)
                    limits.append({
                        "name": agent_name,
                        "rpm_used": rpm_used,
                        "rpm_max": rpm_max,
                        "rpm_pct": min(100, int(rpm_used / max(rpm_max, 1) * 100)),
                        "tpm_used": tpm_used,
                        "tpm_max": tpm_max,
                        "tpm_pct": min(100, int(tpm_used / max(tpm_max, 1) * 100)),
                    })
        except Exception:
            pass
        tmpl = _templates.get_template("partials/rate_limits.html")
        return HTMLResponse(tmpl.render(limits=limits))

    @app.get("/ui/partials/cortex", response_class=HTMLResponse, include_in_schema=False)
    async def partial_cortex():
        stats = {"nodes": 0, "edges": 0, "entities": 0, "triples": 0}
        try:
            from danny_toolkit.brain.cortex import TheCortex
            cortex = TheCortex()
            if hasattr(cortex, "get_stats"):
                stats.update(cortex.get_stats())
            else:
                if cortex._graph is not None:
                    stats["nodes"] = cortex._graph.number_of_nodes()
                    stats["edges"] = cortex._graph.number_of_edges()
        except Exception:
            pass
        tmpl = _templates.get_template("partials/cortex_stats.html")
        return HTMLResponse(tmpl.render(stats=stats))

    @app.get("/ui/partials/pipeline-metrics", response_class=HTMLResponse, include_in_schema=False)
    async def partial_pipeline_metrics():
        metrics = {}
        cache_stats = {}
        try:
            from swarm_engine import get_pipeline_metrics
            metrics = get_pipeline_metrics()
        except ImportError:
            pass
        try:
            from danny_toolkit.core.response_cache import get_response_cache
            cache_stats = get_response_cache().stats()
        except ImportError:
            pass
        tmpl = _templates.get_template("partials/pipeline_metrics.html")
        return HTMLResponse(tmpl.render(metrics=metrics, cache=cache_stats))

    @app.get("/ui/events", include_in_schema=False)
    async def sse_events():
        """SSE stream — polls NeuralBus elke 2s voor nieuwe events."""
        async def _event_generator():
            last_seen = 0
            while True:
                try:
                    from danny_toolkit.core.neural_bus import get_bus
                    bus = get_bus()
                    all_events = []
                    for event_type, history in bus._history.items():
                        for evt in history:
                            all_events.append(evt)
                    # Sort by timestamp, newest first
                    all_events.sort(
                        key=lambda e: e.timestamp if hasattr(e, "timestamp") else "",
                        reverse=True,
                    )
                    for evt in all_events[:5]:
                        evt_hash = hash(
                            (evt.event_type, str(evt.timestamp))
                        )
                        if evt_hash != last_seen:
                            last_seen = evt_hash
                            data = {
                                "event_type": evt.event_type,
                                "bron": evt.bron,
                                "timestamp": evt.timestamp.strftime("%H:%M:%S")
                                if hasattr(evt.timestamp, "strftime")
                                else str(evt.timestamp),
                                "summary": str(evt.data)[:120],
                            }
                            tmpl = _templates.get_template(
                                "partials/event_feed.html"
                            )
                            html = tmpl.render(event=data)
                            yield f"data: {html}\n\n"
                except Exception:
                    pass
                await asyncio.sleep(2)

        return StreamingResponse(
            _event_generator(),
            media_type="text/event-stream",
        )

    @app.get(
        "/api/v1/metrics",
        summary="Systeem metrics (JSON)",
        tags=["Systeem"],
    )
    async def metrics(
        _key: str = Depends(verify_api_key),
    ):
        """JSON metrics endpoint — auth-protected."""
        brain = _get_brain()
        result = {"agents": 0, "uptime": 0.0}
        if hasattr(brain, "nodes"):
            result["agents"] = len(brain.nodes)
        result["uptime"] = round(time.time() - _SERVER_START_TIME, 1)
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            result["memory_mb"] = round(
                proc.memory_info().rss / (1024 * 1024), 1
            )
            result["cpu_percent"] = proc.cpu_percent()
        except Exception:
            pass
        return result


# ─── ENTRY POINT ───────────────────────────────────

def main():
    """Start de FastAPI server."""
    print(
        f"\n  Danny Toolkit API — "
        f"http://localhost:{FASTAPI_PORT}/docs\n"
    )
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=FASTAPI_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
