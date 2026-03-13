# LINE 1: The Gate MUST be first.
import danny_toolkit.core.sovereign_gate  # noqa: F401, E402
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
    Cookie,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
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

# Project root (voor pad-resolutie)
_ROOT = str(Path(__file__).parent)

# .env laden
load_dotenv(Path(__file__).parent / ".env")

# Secret key: uit .env, of random fallback (geldig tot herstart)
import secrets as _secrets
_DEFAULT_SECRET = _secrets.token_urlsafe(32)
FASTAPI_SECRET_KEY = os.getenv("FASTAPI_SECRET_KEY", "")
if not FASTAPI_SECRET_KEY:
    FASTAPI_SECRET_KEY = _DEFAULT_SECRET
    logger.warning(
        "FASTAPI_SECRET_KEY niet ingesteld — random key gegenereerd. "
        "Stel in via .env voor persistente auth."
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
    error_count: int = 0
    trace_id: str = ""  # Phase 31: request correlation ID


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
    # Phase 31: Waakhuis health + circuit breakers
    waakhuis_health: Dict[str, Any] = {}
    circuit_breakers: Dict[str, Any] = {}


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


class TraceSpanResponse(BaseModel):
    """Eén span in een request trace."""
    fase: str
    agent: str = ""
    status: str
    duration_ms: float
    details: Dict[str, Any] = {}


class TraceResponse(BaseModel):
    """Volledige request trace."""
    trace_id: str
    start: float
    duration_ms: float
    spans: List[TraceSpanResponse]
    fouten: List[str] = []
    afgerond: bool = True


class TraceSummaryResponse(BaseModel):
    """Compacte trace samenvatting voor lijstweergave."""
    trace_id: str
    duration_ms: float
    span_count: int
    error_count: int
    status: str


# ─── Phase 38: Observatory Response Models ────────

class AuditSchendingResponse(BaseModel):
    """Eén configuratie-schending."""
    categorie: str = ""
    ernst: str = ""
    beschrijving: str = ""
    sleutel: str = ""


class AuditRapportResponse(BaseModel):
    """Response van /api/v1/config/audit."""
    veilig: bool = True
    schendingen: List[AuditSchendingResponse] = []
    drift_gedetecteerd: bool = False
    gecontroleerd: int = 0
    timestamp: str = ""


class ShardStatistiekResponse(BaseModel):
    """Eén shard statistiek."""
    naam: str
    aantal_chunks: int = 0


class FoutDefinitieResponse(BaseModel):
    """Eén fout definitie uit het register."""
    naam: str
    ernst: str
    strategie: str
    beschrijving: str
    retry_max: int = 0


class FoutContextResponse(BaseModel):
    """Eén recent opgetreden fout."""
    fout_id: str = ""
    fout_type: str = ""
    agent: str = ""
    ernst: str = ""
    strategie: str = ""
    bericht: str = ""
    trace_id: str = ""
    timestamp: float = 0.0
    herstel_geprobeerd: bool = False
    herstel_gelukt: bool = False


class PruningStatsResponse(BaseModel):
    """Response van /api/v1/pruning/stats."""
    totaal_gevolgd: int = 0
    entropy_drempel: float = 0.0
    redundantie_drempel: float = 0.0
    verval_dagen: int = 0
    pruning_enabled: bool = False
    cold_collection: str = ""


class BusStatsResponse(BaseModel):
    """Response van /api/v1/bus/stats."""
    subscribers: int = 0
    event_types_actief: int = 0
    events_in_history: int = 0
    events_gepubliceerd: int = 0
    events_afgeleverd: int = 0
    fouten: int = 0


# ─── Phase 39: Deep Observatory Response Models ──

class SchildStatsResponse(BaseModel):
    """Response van /api/v1/schild/stats."""
    beoordeeld: int = 0
    geblokkeerd: int = 0
    waarschuwingen: int = 0
    doorgelaten: int = 0


class TribunalStatsResponse(BaseModel):
    """Response van /api/v1/tribunal/stats."""
    accepted: int = 0
    retried: int = 0
    failed: int = 0
    total: int = 0
    acceptance_rate: str = "N/A"


class AlertEntryResponse(BaseModel):
    """Eén alert in de historie."""
    timestamp: float = 0.0
    niveau: str = ""
    bericht: str = ""
    bron: str = ""


class AlertHistoryResponse(BaseModel):
    """Response van /api/v1/alerts/history."""
    history: List[AlertEntryResponse] = []
    stats: Dict[str, Any] = {}


class BlackBoxStatsResponse(BaseModel):
    """Response van /api/v1/blackbox/stats."""
    recorded_failures: int = 0
    active_antibodies: int = 0
    total_antibodies: int = 0
    by_severity: Dict[str, int] = {}
    strongest: Any = None
    total_encounters: int = 0


class SynapsePathwayResponse(BaseModel):
    """Eén synapse pathway."""
    category: str = ""
    agent: str = ""
    strength: float = 0.0
    fires: int = 0
    successes: int = 0
    fails: int = 0
    updated: str = ""


class SynapseStatsResponse(BaseModel):
    """Response van /api/v1/synapse/stats."""
    pathways: int = 0
    interactions: int = 0
    avg_strength: float = 0.0
    positive_signals: int = 0
    negative_signals: int = 0
    top_pathways: List[SynapsePathwayResponse] = []


class PhantomPredictionResponse(BaseModel):
    """Eén phantom prediction."""
    category: str = ""
    confidence: float = 0.0
    basis: str = ""
    timestamp: str = ""


class PhantomAccuracyResponse(BaseModel):
    """Response van /api/v1/phantom/accuracy."""
    total_predictions: int = 0
    hits: int = 0
    accuracy: float = 0.0
    pre_warmed: int = 0
    warm_hit_rate: float = 0.0
    predictions: List[PhantomPredictionResponse] = []


# ─── Phase 40: Swarm Sovereignty Models ──

class GoalRequest(BaseModel):
    """Request body voor POST /api/v1/swarm/goal."""
    goal: str = Field(..., min_length=1, max_length=5000,
                      description="High-level doel om te decomponeren en uit te voeren")
    use_models: bool = Field(False,
                             description="Dispatch naar externe AI-modellen (Generaal Mode)")


class SwarmTaskResponse(BaseModel):
    """Eén sub-taak binnen een GoalResponse."""
    task_id: str = ""
    beschrijving: str = ""
    categorie: str = ""
    toegewezen_agent: str = ""
    status: str = ""
    resultaat_preview: str = ""


class GoalResponse(BaseModel):
    """Response van POST /api/v1/swarm/goal."""
    goal: str = ""
    status: str = ""
    taken: List[SwarmTaskResponse] = []
    synthese: str = ""
    execution_time: float = 0.0
    trace_id: str = ""


# ─── Phase 41: Model Registry Models ──

class ModelRegistryResponse(BaseModel):
    """Response van GET /api/v1/models/registry."""
    models: List[dict] = []
    total: int = 0
    available: int = 0


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


async def verify_ui_key(
    key: str = Query(None, description="API key via query param"),
    x_api_key: str = Header(None, description="API key via header"),
    ui_token: str = Cookie(None, description="API key via cookie"),
):
    """Auth voor UI routes — accepteert query param, header, of cookie."""
    token = key or x_api_key or ui_token
    if not token or token != FASTAPI_SECRET_KEY:
        raise HTTPException(
            status_code=401,
            detail="Authenticatie vereist. Gebruik ?key=<secret> of X-API-Key header.",
        )
    return token


def _set_ui_cookie(response: Response) -> Response:
    """Zet/ververs ui_token cookie op een response."""
    response.set_cookie(
        key="ui_token",
        value=FASTAPI_SECRET_KEY,
        httponly=True,
        samesite="strict",
        max_age=86400,
    )
    return response


# ─── APP ────────────────────────────────────────────

app = FastAPI(
    title="Danny Toolkit API — Golden Master v6.11.0",
    description=(
        "## Omega Sovereign Core REST API\n\n"
        "176+ modules | 48 test suites | Phase 52+\n\n"
        "### Endpoints\n"
        "- **Swarm**: Query de SwarmEngine, bekijk agents, decomponeer doelen\n"
        "- **Systeem**: Health checks, heartbeat, metrics, configuratie\n"
        "- **RAG**: Document upload en indexering via ChromaDB\n"
        "- **Tracing**: Request tracing met trace_id correlatie\n"
        "- **Observatory**: Real-time monitoring, leaderboards, kosten, fouten\n"
        "- **Models**: Model registry, provider status, capabilities\n\n"
        "### Authenticatie\n"
        "Alle endpoints vereisen `X-API-Key` header.\n"
    ),
    version="6.11.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Swarm",
            "description": "SwarmEngine queries, agent overzicht, goal decomposition. "
            "Stuur prompts naar het 17-agent netwerk met AdaptiveRouter en circuit breakers.",
        },
        {
            "name": "Systeem",
            "description": "Health probes, heartbeat daemon, metrics en configuratie. "
            "Inclusief Groq reachability, CorticalStack status en disk monitoring.",
        },
        {
            "name": "RAG",
            "description": "Retrieval-Augmented Generation pipeline. "
            "Upload documenten (.txt, .md, .py, .json, .csv) naar ChromaDB via TheLibrarian.",
        },
        {
            "name": "Tracing",
            "description": "Distributed request tracing. Elke SwarmEngine run krijgt een "
            "uniek 8-char hex trace_id. Bekijk traces en spans per request.",
        },
        {
            "name": "Observatory",
            "description": "Real-time system observatory. Dashboards, leaderboards, "
            "auction logs, kostenanalyse, foutstatistieken, NeuralBus events, "
            "BlackBox immune memory, Synapse pathways en Phantom predictions.",
        },
        {
            "name": "Models",
            "description": "Multi-model registry met 5 provider workers. "
            "Bekijk beschikbare modellen, capabilities en auction-based routing.",
        },
        {
            "name": "System",
            "description": "Systeem introspectie en wiring overzicht. "
            "Module inventaris, singleton status en dependency graph.",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:8000",
        "http://localhost:8501",
        "http://localhost:8502",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Optimalisatie 1: Process-time header (latentie monitoring) ───
@app.middleware("http")
async def add_process_time_header(request, call_next):
    """Meet en rapporteer request-latentie via X-Process-Time header."""
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - start) * 1000:.1f}ms"
    return response


# ─── Optimalisatie 2: Lightweight response cache (health/status) ───
_response_ttl_cache: Dict[str, tuple] = {}  # key -> (timestamp, data)
_CACHE_TTL = 2.0  # 2 seconden TTL voor status endpoints


def _cached_response(cache_key: str, ttl: float = _CACHE_TTL):
    """Check TTL cache, retourneer (hit, data)."""
    entry = _response_ttl_cache.get(cache_key)
    if entry and (time.time() - entry[0]) < ttl:
        return True, entry[1]
    return False, None


def _set_cache(cache_key: str, data):
    """Sla response op in TTL cache."""
    _response_ttl_cache[cache_key] = (time.time(), data)


# ─── Optimalisatie 3: SwarmEngine singleton (vermijd herhaalde init) ───
_swarm_engine_instance = None


def _get_swarm_engine(brain=None):
    """Lazy singleton SwarmEngine — vermijdt 50-100ms init per request."""
    global _swarm_engine_instance
    if _swarm_engine_instance is None:
        from swarm_engine import SwarmEngine
        _swarm_engine_instance = SwarmEngine(brain=brain or _get_brain())
    return _swarm_engine_instance


@app.on_event("startup")
async def _startup_event():
    """Auto-discover beschikbare modellen bij server start."""
    try:
        from danny_toolkit.brain.model_sync import get_model_registry
        registry = get_model_registry()
        registry.auto_discover()
        logger.info("Model Registry: auto_discover() voltooid")
    except Exception as e:
        logger.debug("Model Registry auto_discover failed: %s", e)


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
    response: Response,
    _key: str = Depends(verify_api_key),
):
    """Verwerk een prompt via de SwarmEngine en
    retourneer de resultaten als SwarmPayload lijst.
    """
    brain = _get_brain()

    if req.stream:
        return await _stream_response(req.message, brain)

    start = time.time()
    engine = _get_swarm_engine(brain)

    try:
        payloads = await engine.run(req.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SwarmEngine fout: {e}",
        )

    elapsed = round(time.time() - start, 2)
    errors = sum(1 for p in payloads if p.type == "error")

    # Phase 31: trace_id uit eerste payload + response header
    trace_id = ""
    if payloads and hasattr(payloads[0], "trace_id"):
        trace_id = payloads[0].trace_id or ""
    if trace_id:
        response.headers["X-Trace-Id"] = trace_id

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
        error_count=errors,
        trace_id=trace_id,
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
    summary="L1 Pulse — razendsnelle health check (<100ms)",
    tags=["Systeem"],
)
async def health_pulse(
    _key: str = Depends(verify_api_key),
):
    """Ultra-lichte health check voor monitoring/k8s probes.

    Geen brain loading, geen externe API calls, geen DB writes.
    Antwoordt in <100ms.
    """
    uptime = time.time() - _SERVER_START_TIME
    return {
        "status": "online",
        "version": "6.11.0",
        "uptime_seconds": round(uptime, 1),
        "timestamp": datetime.now().isoformat(),
    }


@app.get(
    "/api/v1/health/deep",
    response_model=HealthResponse,
    summary="L3 Deep Scan — volledige systeemdiagnose",
    tags=["Systeem"],
)
async def health_deep(
    _key: str = Depends(verify_api_key),
):
    """Uitgebreide gezondheidscheck: brain, Governor, Groq,
    CorticalStack, disk, agents, caches, circuit breakers.
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

    # Phase 31: WaakhuisMonitor health + circuit breakers
    waakhuis_data = {}
    try:
        from danny_toolkit.brain.waakhuis import get_waakhuis
        waakhuis_data = get_waakhuis().gezondheidsrapport()
    except Exception as e:
        logger.debug("Waakhuis health check error: %s", e)

    circuit_data = {}
    try:
        from swarm_engine import get_circuit_state
        circuit_data = get_circuit_state()
    except ImportError:
        pass

    return HealthResponse(
        status="ONLINE",
        brain_online=brain.is_online,
        governor_status=gov_status,
        circuit_breaker=cb_status,
        timestamp=datetime.now().isoformat(),
        version="6.11.0",
        uptime_seconds=round(uptime, 1),
        memory_mb=round(mem_mb, 1),
        active_agents=actief,
        groq_reachable=groq_ok,
        cortical_stack_writable=stack_ok,
        disk_free_gb=disk_free,
        agents_in_cooldown=cooldown_count,
        agent_metrics=agent_m,
        response_cache=cache_stats,
        waakhuis_health=waakhuis_data,
        circuit_breakers=circuit_data,
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


# ─── G2: CorticalStack Memory ────────────────────────


@app.get(
    "/api/v1/memory/recent",
    summary="Recente episodische herinneringen uit de CorticalStack",
    tags=["System"],
)
async def memory_recent(
    count: int = Query(default=20, ge=1, le=200),
    _key: str = Depends(verify_api_key),
):
    """Haal de laatste N events uit episodic_memory op.

    Lichte read-only query — geen brain loading nodig.
    """
    try:
        from danny_toolkit.brain.cortical_stack import get_cortical_stack
        stack = get_cortical_stack()
        events = stack.get_recent_events(count=count)
        return {
            "count": len(events),
            "events": events,
        }
    except Exception as e:
        logger.error("CorticalStack read mislukt: %s", e)
        raise HTTPException(status_code=503, detail=f"CorticalStack onbereikbaar: {e}")


# ─── G3: GPU Status ──────────────────────────────────


@app.get(
    "/api/v1/gpu/status",
    summary="Realtime GPU status — clocks, VRAM, temperatuur, power",
    tags=["Systeem"],
)
async def gpu_status(
    _key: str = Depends(verify_api_key),
):
    """Volledige GPU metrics via vram_manager.

    Combineert torch VRAM info met nvidia-smi clock/power/temp data.
    """
    try:
        from danny_toolkit.core.vram_manager import gpu_status as _gpu_status
        return _gpu_status()
    except Exception as e:
        logger.error("GPU status ophalen mislukt: %s", e)
        return {"beschikbaar": False, "error": str(e)}


# ─── G6: Governor Rate Limits ────────────────────────


@app.get(
    "/api/v1/governor/rate-limits",
    summary="Huidige token-usage en rate-limit status per agent",
    tags=["Observatory"],
)
async def governor_rate_limits(
    _key: str = Depends(verify_api_key),
):
    """Rate-limit overzicht: per-agent tokens, 429 counts, cooldowns.

    Gebruikt SmartKeyManager.get_status() voor volledige diagnostiek.
    """
    try:
        from danny_toolkit.core.key_manager import get_key_manager
        km = get_key_manager()
        status = km.get_status()
        # Voeg agents in cooldown toe
        status["agents_in_cooldown"] = list(km.get_agents_in_cooldown())
        return status
    except Exception as e:
        logger.error("Rate-limit status ophalen mislukt: %s", e)
        raise HTTPException(status_code=503, detail=f"KeyManager onbereikbaar: {e}")


# ─── G4: Advanced Knowledge Search ───────────────────


@app.get(
    "/api/v1/knowledge/search",
    summary="Doorzoek de 422 OMEGA Advanced Knowledge documenten",
    tags=["RAG"],
)
async def knowledge_search(
    query: str = Query(..., min_length=2, max_length=500, description="Zoekopdracht"),
    n_results: int = Query(default=5, ge=1, le=20),
    _key: str = Depends(verify_api_key),
):
    """Doorzoek de omega_advanced_skills ChromaDB collectie.

    Bevat alle 15+ kennisdocumenten over architectuur, protocollen,
    skills, quests, persona en UI-design. Draait thread-geïsoleerd
    om asyncio event loop clashes te voorkomen.
    """
    try:
        from danny_toolkit.core.advanced_knowledge_bridge import AdvancedKnowledgeBridge
        bridge = AdvancedKnowledgeBridge()
        result = bridge.raadpleeg_omega_skills(query=query, n_results=n_results)
        if "error" in result:
            raise HTTPException(status_code=503, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Advanced Knowledge search mislukt: %s", e)
        raise HTTPException(status_code=503, detail=f"Knowledge Bridge onbereikbaar: {e}")


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


# ─── TRACING ENDPOINTS (Phase 36) ─────────────────

@app.get(
    "/api/v1/trace/{trace_id}",
    response_model=TraceResponse,
    summary="Haal een request trace op",
    tags=["Tracing"],
)
async def get_trace(
    trace_id: str,
    _key: str = Depends(verify_api_key),
):
    """Haal een volledige request trace op via trace_id."""
    try:
        from danny_toolkit.core.request_tracer import (
            get_request_tracer,
        )
        tracer = get_request_tracer()
        trace = tracer.get_trace(trace_id)
        if trace is None:
            raise HTTPException(
                status_code=404,
                detail=f"Trace {trace_id} niet gevonden",
            )
        d = trace.to_dict()
        return TraceResponse(
            trace_id=d["trace_id"],
            start=d["start"],
            duration_ms=d["duration_ms"],
            spans=[
                TraceSpanResponse(**s) for s in d["spans"]
            ],
            fouten=d["fouten"],
            afgerond=d["afgerond"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Trace ophalen mislukt: {e}",
        )


@app.get(
    "/api/v1/traces",
    response_model=List[TraceSummaryResponse],
    summary="Lijst recente request traces",
    tags=["Tracing"],
)
async def list_traces(
    count: int = 20,
    _key: str = Depends(verify_api_key),
):
    """Haal recente request traces op als samenvatting."""
    try:
        from danny_toolkit.core.request_tracer import (
            get_request_tracer,
        )
        tracer = get_request_tracer()
        traces = tracer.get_recent(count=min(count, 100))
        return [
            TraceSummaryResponse(**t.to_summary())
            for t in traces
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Traces ophalen mislukt: {e}",
        )


# ─── Phase 38: OMEGA OBSERVATORY ENDPOINTS ────────

@app.get(
    "/api/v1/config/audit",
    response_model=AuditRapportResponse,
    summary="Voer configuratie-audit uit",
    tags=["Observatory"],
)
async def config_audit(
    _key: str = Depends(verify_api_key),
):
    """Trigger ConfigAuditor.audit() en retourneer rapport."""
    try:
        from danny_toolkit.brain.config_auditor import get_config_auditor
        auditor = get_config_auditor()
        rapport = auditor.audit()
        return AuditRapportResponse(
            veilig=rapport.veilig,
            schendingen=[
                AuditSchendingResponse(
                    categorie=getattr(s, "categorie", ""),
                    ernst=getattr(s, "ernst", ""),
                    beschrijving=getattr(s, "beschrijving", ""),
                    sleutel=getattr(s, "sleutel", ""),
                )
                for s in rapport.schendingen
            ],
            drift_gedetecteerd=rapport.drift_gedetecteerd,
            gecontroleerd=rapport.gecontroleerd,
            timestamp=getattr(rapport, "timestamp", ""),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Config audit mislukt: {e}",
        )


@app.get(
    "/api/v1/shards/stats",
    response_model=List[ShardStatistiekResponse],
    summary="Shard statistieken opvragen",
    tags=["Observatory"],
)
async def shard_stats(
    _key: str = Depends(verify_api_key),
):
    """Haal ShardRouter statistieken op."""
    try:
        from danny_toolkit.core.shard_router import get_shard_router
        router = get_shard_router()
        stats = router.statistieken()
        return [
            ShardStatistiekResponse(
                naam=s.naam, aantal_chunks=s.aantal_chunks,
            )
            for s in stats
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Shard stats mislukt: {e}",
        )


@app.get(
    "/api/v1/errors/taxonomy",
    response_model=List[FoutDefinitieResponse],
    summary="Lijst alle fout-definities",
    tags=["Observatory"],
)
async def error_taxonomy(
    _key: str = Depends(verify_api_key),
):
    """Retourneer het volledige FOUT_REGISTER."""
    try:
        from danny_toolkit.core.error_taxonomy import FOUT_REGISTER
        return [
            FoutDefinitieResponse(
                naam=fd.naam,
                ernst=fd.ernst.value,
                strategie=fd.strategie.value,
                beschrijving=fd.beschrijving,
                retry_max=fd.retry_max,
            )
            for fd in FOUT_REGISTER.values()
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Taxonomy ophalen mislukt: {e}",
        )


@app.get(
    "/api/v1/errors/recent",
    response_model=List[FoutContextResponse],
    summary="Recente fout-contexten",
    tags=["Observatory"],
)
async def recent_errors(
    count: int = 50,
    _key: str = Depends(verify_api_key),
):
    """Retourneer recente FoutContext objecten uit de ring buffer."""
    try:
        from swarm_engine import get_recent_errors
        errors = get_recent_errors(count=min(count, 200))
        return [
            FoutContextResponse(**fc.to_dict())
            for fc in errors
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recente fouten ophalen mislukt: {e}",
        )


@app.get(
    "/api/v1/pruning/stats",
    response_model=PruningStatsResponse,
    summary="SelfPruning statistieken",
    tags=["Observatory"],
)
async def pruning_stats(
    _key: str = Depends(verify_api_key),
):
    """Haal SelfPruning statistieken op."""
    try:
        from danny_toolkit.core.self_pruning import get_self_pruning
        sp = get_self_pruning()
        stats = sp.statistieken()
        return PruningStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Pruning stats mislukt: {e}",
        )


@app.post(
    "/api/v1/pruning/run",
    summary="Trigger pruning cycle",
    tags=["Observatory"],
)
async def pruning_run(
    _key: str = Depends(verify_api_key),
):
    """Start een SelfPruning.prune() on-demand."""
    try:
        from danny_toolkit.core.self_pruning import get_self_pruning
        sp = get_self_pruning()
        resultaat = sp.prune()
        return resultaat
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Pruning run mislukt: {e}",
        )


@app.get(
    "/api/v1/bus/stats",
    response_model=BusStatsResponse,
    summary="NeuralBus statistieken",
    tags=["Observatory"],
)
async def bus_stats(
    _key: str = Depends(verify_api_key),
):
    """Haal NeuralBus statistieken op."""
    try:
        from danny_toolkit.core.neural_bus import get_bus
        bus = get_bus()
        stats = bus.statistieken()
        return BusStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Bus stats mislukt: {e}",
        )


# ─── Phase 39: DEEP OBSERVATORY ENDPOINTS ─────────

@app.get(
    "/api/v1/schild/stats",
    response_model=SchildStatsResponse,
    summary="HallucinatieSchild statistieken",
    tags=["Observatory"],
)
async def schild_stats(
    _key: str = Depends(verify_api_key),
):
    """Haal HallucinatieSchild statistieken op."""
    try:
        from danny_toolkit.brain.hallucination_shield import (
            get_hallucination_shield,
        )
        stats = get_hallucination_shield().get_stats()
        return SchildStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Schild stats mislukt: {e}",
        )


@app.get(
    "/api/v1/tribunal/stats",
    response_model=TribunalStatsResponse,
    summary="AdversarialTribunal statistieken",
    tags=["Observatory"],
)
async def tribunal_stats(
    _key: str = Depends(verify_api_key),
):
    """Haal AdversarialTribunal statistieken op."""
    try:
        from danny_toolkit.brain.adversarial_tribunal import (
            get_adversarial_tribunal,
        )
        stats = get_adversarial_tribunal().get_stats()
        return TribunalStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Tribunal stats mislukt: {e}",
        )


@app.get(
    "/api/v1/alerts/history",
    response_model=AlertHistoryResponse,
    summary="Alert historie en statistieken",
    tags=["Observatory"],
)
async def alerts_history(
    count: int = 50,
    _key: str = Depends(verify_api_key),
):
    """Haal alert historie en stats op via Alerter singleton."""
    try:
        from danny_toolkit.core.alerter import get_alerter
        alerter = get_alerter()
        history = alerter.get_history(count=min(count, 200))
        stats = alerter.get_alert_stats()
        return AlertHistoryResponse(
            history=[
                AlertEntryResponse(**h) for h in history
            ],
            stats=stats,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Alert history mislukt: {e}",
        )


@app.get(
    "/api/v1/blackbox/stats",
    response_model=BlackBoxStatsResponse,
    summary="BlackBox immune system statistieken",
    tags=["Observatory"],
)
async def blackbox_stats(
    _key: str = Depends(verify_api_key),
):
    """Haal BlackBox immune system statistieken op."""
    try:
        from danny_toolkit.brain.black_box import get_black_box
        stats = get_black_box().get_stats()
        return BlackBoxStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"BlackBox stats mislukt: {e}",
        )


@app.get(
    "/api/v1/synapse/stats",
    response_model=SynapseStatsResponse,
    summary="TheSynapse pathway statistieken",
    tags=["Observatory"],
)
async def synapse_stats(
    _key: str = Depends(verify_api_key),
):
    """Haal TheSynapse statistieken en top pathways op."""
    try:
        from danny_toolkit.brain.synapse import TheSynapse
        synapse = TheSynapse()
        stats = synapse.get_stats()
        top = synapse.get_top_pathways(limit=20)
        return SynapseStatsResponse(
            **stats,
            top_pathways=[
                SynapsePathwayResponse(**p) for p in top
            ],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Synapse stats mislukt: {e}",
        )


@app.get(
    "/api/v1/phantom/accuracy",
    response_model=PhantomAccuracyResponse,
    summary="ThePhantom voorspellings-nauwkeurigheid",
    tags=["Observatory"],
)
async def phantom_accuracy(
    _key: str = Depends(verify_api_key),
):
    """Haal ThePhantom nauwkeurigheid en actieve voorspellingen op."""
    try:
        from danny_toolkit.brain.phantom import ThePhantom
        phantom = ThePhantom()
        acc = phantom.get_accuracy()
        preds = phantom.get_predictions()
        return PhantomAccuracyResponse(
            **acc,
            predictions=[
                PhantomPredictionResponse(**p) for p in preds
            ],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Phantom accuracy mislukt: {e}",
        )


# ─── Phase 40: Swarm Sovereignty Endpoint ──

@app.post(
    "/api/v1/swarm/goal",
    response_model=GoalResponse,
    summary="Decomponeer en voer een high-level goal uit via TaskArbitrator",
    tags=["Swarm"],
)
async def swarm_goal(
    req: GoalRequest,
    _key: str = Depends(verify_api_key),
):
    """Decomponeer een goal in sub-taken, wijs agents toe via auction,
    voer parallel uit, en synthetiseer het resultaat."""
    import time as _time
    t0 = _time.time()
    try:
        from swarm_engine import SwarmEngine
        from danny_toolkit.brain.arbitrator import get_arbitrator

        engine = SwarmEngine(brain=_get_brain())
        arbitrator = get_arbitrator(brain=_get_brain())

        # Decompose + Execute (Generaal Mode of Swarm Mode)
        manifest = await arbitrator.decompose(req.goal)
        if req.use_models:
            manifest = await arbitrator.execute_with_models(manifest)
        else:
            manifest = await arbitrator.execute(manifest, engine=engine)

        synthese = arbitrator.synthesize(manifest)
        elapsed = _time.time() - t0

        return GoalResponse(
            goal=manifest.goal,
            status=manifest.status,
            taken=[
                SwarmTaskResponse(**t.to_dict())
                for t in manifest.taken
            ],
            synthese=synthese,
            execution_time=round(elapsed, 3),
            trace_id=manifest.trace_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Swarm goal execution mislukt: {e}",
        )


# ─── Phase 41: Model Registry ─────────────────────

@app.get(
    "/api/v1/models/registry",
    response_model=ModelRegistryResponse,
    summary="Lijst beschikbare externe AI-modellen",
    tags=["Models"],
)
async def models_registry(
    _key: str = Depends(verify_api_key),
):
    """Geeft een overzicht van alle geregistreerde modellen en hun status."""
    try:
        from danny_toolkit.brain.model_sync import get_model_registry
        registry = get_model_registry()
        stats = registry.get_stats()
        return ModelRegistryResponse(
            models=stats.get("workers", []),
            total=stats.get("total_workers", 0),
            available=stats.get("available_workers", 0),
        )
    except ImportError:
        return ModelRegistryResponse(models=[], total=0, available=0)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Model registry ophalen mislukt: {e}",
        )


# ─── Phase 42: System Introspection ───────────────

class IntrospectionResponse(BaseModel):
    """Response van GET /api/v1/system/introspection."""
    versie: str = ""
    gezondheid_score: float = 0.0
    modules_actief: int = 0
    modules_totaal: int = 0
    wirings_actief: int = 0
    wirings_totaal: int = 0
    security_score: float = 0.0
    security_details: dict = {}
    timestamp: str = ""


@app.get(
    "/api/v1/system/introspection",
    response_model=IntrospectionResponse,
    summary="Systeem zelfdiagnose — gezondheid, wirings, security",
    tags=["System"],
)
async def system_introspection(
    _key: str = Depends(verify_api_key),
):
    """Het systeem onderzoekt zichzelf: modules, wirings, beveiliging."""
    try:
        from danny_toolkit.brain.introspector import get_introspector
        intro = get_introspector()
        report = intro.get_health_report()
        return IntrospectionResponse(**report)
    except ImportError:
        return IntrospectionResponse()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Introspectie mislukt: {e}",
        )


@app.get(
    "/api/v1/system/wirings",
    summary="Cross-module wiring map",
    tags=["System"],
)
async def system_wirings(
    _key: str = Depends(verify_api_key),
):
    """Toont alle cross-module verbindingen en hun status."""
    try:
        from danny_toolkit.brain.introspector import get_introspector
        intro = get_introspector()
        return {"wiring_map": intro.get_wiring_map()}
    except ImportError:
        return {"wiring_map": "Introspector niet beschikbaar"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Wiring map ophalen mislukt: {e}",
        )


# ─── Phase 42: Observatory Sync (Generaal Controlekamer) ──

class ModelObservatoryEntryResponse(BaseModel):
    """Eén model in het observatory overzicht."""
    provider: str = ""
    model_id: str = ""
    calls: int = 0
    successes: int = 0
    failures: int = 0
    barrier_rejections: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate: float = 0.0
    cost_tier: int = 1
    latency_class: int = 1
    circuit_open: bool = False
    beschikbaar: bool = True
    rank: int = 0


class AuctionLogEntryResponse(BaseModel):
    """Eén veiling in het auction log."""
    timestamp: float = 0.0
    task_id: str = ""
    task_categorie: str = ""
    winnaar_provider: str = ""
    winnaar_model_id: str = ""
    winnaar_score: float = 0.0
    deelnemers: int = 0
    barrier_pass: Any = None


class ObservatoryDashboardResponse(BaseModel):
    """Response van GET /api/v1/observatory/dashboard."""
    totaal_modellen: int = 0
    beschikbare_modellen: int = 0
    totaal_calls: int = 0
    totaal_tokens: int = 0
    totaal_successen: int = 0
    totaal_failures: int = 0
    totaal_barrier_rejections: int = 0
    gemiddelde_latency_ms: float = 0.0
    gemiddelde_success_rate: float = 0.0
    goals_processed: int = 0
    tasks_decomposed: int = 0
    model_auctions_held: int = 0
    model_tasks_completed: int = 0
    model_tasks_failed: int = 0
    barrier_rejections_arbitrator: int = 0
    modellen: List[Dict[str, Any]] = []
    recente_veilingen: List[Dict[str, Any]] = []
    timestamp: str = ""


class CostAnalysisResponse(BaseModel):
    """Response van GET /api/v1/observatory/costs."""
    per_provider: Dict[str, Any] = {}
    per_model: List[Dict[str, Any]] = []
    aanbevelingen: List[str] = []


class FailureAnalysisResponse(BaseModel):
    """Response van GET /api/v1/observatory/failures."""
    modellen: List[Dict[str, Any]] = []
    probleemmodellen: List[Dict[str, Any]] = []
    totaal_failures: int = 0
    totaal_barrier_rejections: int = 0
    circuit_open_count: int = 0


class ObservatoryStatsResponse(BaseModel):
    """Response van GET /api/v1/observatory/stats."""
    snapshots_taken: int = 0
    leaderboard_queries: int = 0
    auction_logs_recorded: int = 0
    auction_log_size: int = 0
    snapshot_history_size: int = 0


@app.get(
    "/api/v1/observatory/dashboard",
    response_model=ObservatoryDashboardResponse,
    summary="Generaal controlekamer — live model statistieken",
    tags=["Observatory"],
)
async def observatory_dashboard(
    _key: str = Depends(verify_api_key),
):
    """Compleet observatory dashboard met model stats, arbitrator stats,
    en recente veilingen."""
    try:
        from danny_toolkit.brain.observatory_sync import get_observatory_sync
        obs = get_observatory_sync()
        data = obs.get_dashboard_data()
        return ObservatoryDashboardResponse(**data.to_dict())
    except ImportError:
        return ObservatoryDashboardResponse()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Observatory dashboard mislukt: {e}",
        )


@app.get(
    "/api/v1/observatory/leaderboard",
    response_model=List[ModelObservatoryEntryResponse],
    summary="Model leaderboard — ranking op prestatie",
    tags=["Observatory"],
)
async def observatory_leaderboard(
    sort_by: str = "success_rate",
    _key: str = Depends(verify_api_key),
):
    """Geeft een gerankt overzicht van alle modellen.
    Sorteer op: success_rate, calls, avg_latency_ms, total_tokens, failures."""
    try:
        from danny_toolkit.brain.observatory_sync import get_observatory_sync
        obs = get_observatory_sync()
        leaderboard = obs.get_model_leaderboard(sort_by=sort_by)
        return [ModelObservatoryEntryResponse(**m) for m in leaderboard]
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Observatory leaderboard mislukt: {e}",
        )


@app.get(
    "/api/v1/observatory/auctions",
    response_model=List[AuctionLogEntryResponse],
    summary="Recente model-veilingen",
    tags=["Observatory"],
)
async def observatory_auctions(
    count: int = 50,
    _key: str = Depends(verify_api_key),
):
    """Haal recente model-veiling logs op, nieuwste eerst."""
    try:
        from danny_toolkit.brain.observatory_sync import get_observatory_sync
        obs = get_observatory_sync()
        auctions = obs.get_auction_history(count=min(count, 200))
        return [AuctionLogEntryResponse(**a) for a in auctions]
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Observatory auctions mislukt: {e}",
        )


@app.get(
    "/api/v1/observatory/costs",
    response_model=CostAnalysisResponse,
    summary="Token-verbruik per provider en model",
    tags=["Observatory"],
)
async def observatory_costs(
    _key: str = Depends(verify_api_key),
):
    """Analyseer token-verbruik met aanbevelingen voor optimalisatie."""
    try:
        from danny_toolkit.brain.observatory_sync import get_observatory_sync
        obs = get_observatory_sync()
        costs = obs.get_cost_analysis()
        return CostAnalysisResponse(**costs)
    except ImportError:
        return CostAnalysisResponse()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Observatory cost analysis mislukt: {e}",
        )


@app.get(
    "/api/v1/observatory/failures",
    response_model=FailureAnalysisResponse,
    summary="Faal-analyse per model",
    tags=["Observatory"],
)
async def observatory_failures(
    _key: str = Depends(verify_api_key),
):
    """Analyseer faalpatronen: barrier rejections, circuit opens, errors."""
    try:
        from danny_toolkit.brain.observatory_sync import get_observatory_sync
        obs = get_observatory_sync()
        failures = obs.get_failure_analysis()
        return FailureAnalysisResponse(**failures)
    except ImportError:
        return FailureAnalysisResponse()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Observatory failure analysis mislukt: {e}",
        )


@app.get(
    "/api/v1/observatory/stats",
    response_model=ObservatoryStatsResponse,
    summary="ObservatorySync interne statistieken",
    tags=["Observatory"],
)
async def observatory_stats(
    _key: str = Depends(verify_api_key),
):
    """ObservatorySync eigen statistieken: snapshots, leaderboard queries, etc."""
    try:
        from danny_toolkit.brain.observatory_sync import get_observatory_sync
        obs = get_observatory_sync()
        stats = obs.get_stats()
        return ObservatoryStatsResponse(**stats)
    except ImportError:
        return ObservatoryStatsResponse()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Observatory stats mislukt: {e}",
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
    async def dashboard(_key: str = Depends(verify_ui_key)):
        tmpl = _templates.get_template("dashboard.html")
        return _set_ui_cookie(HTMLResponse(tmpl.render()))

    @app.get("/ui/partials/agents", response_class=HTMLResponse, include_in_schema=False)
    async def partial_agents(_key: str = Depends(verify_ui_key)):
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
        return _set_ui_cookie(HTMLResponse(tmpl.render(agents=agents)))

    @app.get("/ui/partials/governor", response_class=HTMLResponse, include_in_schema=False)
    async def partial_governor(_key: str = Depends(verify_ui_key)):
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
        except Exception as e:
            logger.debug("Governor stats: %s", e)
            stats["Status"] = "NIET BESCHIKBAAR"
        tmpl = _templates.get_template("partials/governor.html")
        return _set_ui_cookie(HTMLResponse(tmpl.render(stats=stats)))

    @app.get("/ui/partials/rate-limits", response_class=HTMLResponse, include_in_schema=False)
    async def partial_rate_limits(_key: str = Depends(verify_ui_key)):
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
        except Exception as e:
            logger.debug("Rate limits: %s", e)
        tmpl = _templates.get_template("partials/rate_limits.html")
        return _set_ui_cookie(HTMLResponse(tmpl.render(limits=limits)))

    @app.get("/ui/partials/cortex", response_class=HTMLResponse, include_in_schema=False)
    async def partial_cortex(_key: str = Depends(verify_ui_key)):
        import math
        nodes, edges, meta, positions = [], [], {}, {}
        kmap_path = os.path.join(_ROOT, "data", "knowledge_map.json")
        try:
            with open(kmap_path, encoding="utf-8") as f:
                kmap = json.load(f)
            nodes = kmap.get("nodes", [])
            edges = kmap.get("edges", [])
            meta = kmap.get("meta", {})
            # Bereken posities: Trinity driehoek layout (geschaald voor 30+ nodes)
            domain_nodes = {"MIND": [], "BODY": [], "SOUL": []}
            for n in nodes:
                domain_nodes.setdefault(n["domain"], []).append(n["id"])
            # MIND = top center, BODY = bottom-left, SOUL = bottom-right
            centers = {"MIND": (280, 80), "BODY": (90, 240), "SOUL": (470, 240)}
            for domain, nids in domain_nodes.items():
                cx, cy = centers.get(domain, (280, 160))
                count = max(len(nids), 1)
                spread = min(55 + count * 5, 100)
                for i, nid in enumerate(nids):
                    angle = 2 * math.pi * i / count - math.pi / 2
                    px = cx + spread * math.cos(angle)
                    py = cy + spread * math.sin(angle)
                    positions[nid] = (round(max(15, min(px, 545))),
                                      round(max(15, min(py, 305))))
        except Exception as e:
            logger.debug("Knowledge map load: %s", e)
            meta = {"total_nodes": 0, "total_edges": 0, "cross_domain_edges": 0,
                    "total_docs": 0, "scan_time_s": 0, "generated": "-"}
        tmpl = _templates.get_template("partials/cortex_stats.html")
        return _set_ui_cookie(HTMLResponse(tmpl.render(
            nodes=nodes, edges=edges, meta=meta, positions=positions)))

    @app.get("/ui/partials/pipeline-metrics", response_class=HTMLResponse, include_in_schema=False)
    async def partial_pipeline_metrics(_key: str = Depends(verify_ui_key)):
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
        sentinel_stats = None
        try:
            from danny_toolkit.brain.eternal_sentinel import get_sentinel
            sentinel_stats = get_sentinel().get_status()
        except Exception:
            pass
        tmpl = _templates.get_template("partials/pipeline_metrics.html")
        return _set_ui_cookie(HTMLResponse(tmpl.render(
            metrics=metrics, cache=cache_stats, sentinel=sentinel_stats)))

    @app.get("/ui/partials/observatory", response_class=HTMLResponse, include_in_schema=False)
    async def partial_observatory(_key: str = Depends(verify_ui_key)):
        dashboard_data = {
            "totaal_modellen": 0,
            "beschikbare_modellen": 0,
            "totaal_calls": 0,
            "totaal_tokens": 0,
            "gemiddelde_latency_ms": 0.0,
            "gemiddelde_success_rate_pct": "0.0",
            "modellen": [],
            "goals_processed": 0,
            "tasks_decomposed": 0,
            "model_auctions_held": 0,
            "barrier_rejections_arbitrator": 0,
        }
        try:
            from danny_toolkit.brain.observatory_sync import get_observatory_sync
            obs = get_observatory_sync()
            raw = obs.get_dashboard_data()
            d = raw.to_dict()
            d["gemiddelde_success_rate_pct"] = str(
                round(d.get("gemiddelde_success_rate", 0) * 100, 1)
            )
            dashboard_data.update(d)
        except Exception as e:
            logger.debug("Observatory partial: %s", e)
        tmpl = _templates.get_template("partials/observatory.html")
        return _set_ui_cookie(HTMLResponse(tmpl.render(dashboard=dashboard_data)))

    # ─── Soul Pulse (G2) ────────────────────────────

    @app.get("/ui/partials/soul-pulse", response_class=HTMLResponse, include_in_schema=False)
    async def partial_soul_pulse(_key: str = Depends(verify_ui_key)):
        events = []
        total = 0
        try:
            from danny_toolkit.brain.cortical_stack import get_cortical_stack
            stack = get_cortical_stack()
            events = stack.get_recent_events(count=10)
            # Totaal events in de stack
            row = stack._conn.execute("SELECT count(*) FROM episodic_memory").fetchone()
            total = row[0] if row else 0
        except Exception as e:
            logger.debug("Soul pulse partial: %s", e)
        tmpl = _templates.get_template("partials/soul_pulse.html")
        return _set_ui_cookie(HTMLResponse(tmpl.render(events=events, total=total)))

    # ─── Body Metrics (G3) ────────────────────────────

    @app.get("/ui/partials/body-metrics", response_class=HTMLResponse, include_in_schema=False)
    async def partial_body_metrics(_key: str = Depends(verify_ui_key)):
        gpu = {"beschikbaar": False}
        try:
            from danny_toolkit.core.vram_manager import gpu_status as _gpu_status
            gpu = _gpu_status()
        except Exception as e:
            logger.debug("Body metrics partial: %s", e)
        tmpl = _templates.get_template("partials/body_metrics.html")
        return _set_ui_cookie(HTMLResponse(tmpl.render(gpu=gpu)))

    # ─── Governor Guard (G6) ──────────────────────────

    @app.get("/ui/partials/governor-guard", response_class=HTMLResponse, include_in_schema=False)
    async def partial_governor_guard(_key: str = Depends(verify_ui_key)):
        status = {}
        try:
            from danny_toolkit.core.key_manager import get_key_manager
            km = get_key_manager()
            status = km.get_status()
            status["agents_in_cooldown"] = list(km.get_agents_in_cooldown())
        except Exception as e:
            logger.debug("Governor guard partial: %s", e)
        tmpl = _templates.get_template("partials/governor_guard.html")
        return _set_ui_cookie(HTMLResponse(tmpl.render(status=status)))

    # ─── Benchmark Results ──────────────────────────

    @app.get("/ui/partials/benchmark", response_class=HTMLResponse, include_in_schema=False)
    async def partial_benchmark(_key: str = Depends(verify_ui_key)):
        benchmark = None
        try:
            import json as _json
            bench_path = Path(__file__).parent / "data" / "benchmark_results.json"
            if bench_path.exists():
                with open(bench_path, "r", encoding="utf-8") as f:
                    benchmark = _json.load(f)
        except Exception as e:
            logger.debug("Benchmark partial: %s", e)
        tmpl = _templates.get_template("partials/benchmark.html")
        return _set_ui_cookie(HTMLResponse(tmpl.render(benchmark=benchmark)))

    @app.get(
        "/api/v1/benchmark",
        summary="Hardware benchmark resultaten",
        tags=["Systeem"],
    )
    async def api_benchmark(_key: str = Depends(verify_api_key)):
        """Retourneer de laatste benchmark resultaten uit data/benchmark_results.json."""
        import json as _json
        bench_path = Path(__file__).parent / "data" / "benchmark_results.json"
        if not bench_path.exists():
            return {"status": "no_data", "message": "Run omega_benchmark.py eerst"}
        with open(bench_path, "r", encoding="utf-8") as f:
            return _json.load(f)

    @app.get("/ui/events", include_in_schema=False)
    async def sse_events(_key: str = Depends(verify_ui_key)):
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
                except Exception as e:
                    logger.debug("SSE event: %s", e)
                await asyncio.sleep(2)

        return StreamingResponse(
            _event_generator(),
            media_type="text/event-stream",
        )

    # ─── RAG Search (ChromaDB) ─────────────────────────

    def _get_chroma_client():
        """Lazy ChromaDB PersistentClient singleton."""
        if not hasattr(_get_chroma_client, "_client"):
            import chromadb
            chroma_dir = str(
                Path(__file__).parent / "data" / "rag" / "chromadb"
            )
            _get_chroma_client._client = chromadb.PersistentClient(
                path=chroma_dir,
            )
        return _get_chroma_client._client

    @app.get(
        "/ui/partials/rag-search",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    async def partial_rag_search(_key: str = Depends(verify_ui_key)):
        """RAG Search card — toont zoekformulier + collectie stats."""
        collections = []
        total_docs = 0
        db_size_mb = "0.0"
        try:
            client = _get_chroma_client()
            for col in client.list_collections():
                count = col.count()
                collections.append({"name": col.name, "count": count})
                total_docs += count
            # Sorteer danny_knowledge eerst
            collections.sort(
                key=lambda c: (c["name"] != "danny_knowledge", c["name"]),
            )
            chroma_db = (
                Path(__file__).parent / "data" / "rag" / "chromadb"
                / "chroma.sqlite3"
            )
            if chroma_db.exists():
                db_size_mb = f"{chroma_db.stat().st_size / (1024*1024):.1f}"
        except Exception as e:
            logger.debug("RAG search init: %s", e)
        tmpl = _templates.get_template("partials/rag_search.html")
        return _set_ui_cookie(HTMLResponse(tmpl.render(
            collections=collections,
            total_docs=total_docs,
            db_size_mb=db_size_mb,
        )))

    @app.post(
        "/ui/partials/rag-search",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    async def partial_rag_search_post(
        request: Request,
        _key: str = Depends(verify_ui_key),
    ):
        """RAG Search — voer zoekopdracht uit op ChromaDB collectie."""
        form = await request.form()
        query = str(form.get("query", "")).strip()
        collection_name = str(form.get("collection", "danny_knowledge"))
        top_k = min(int(form.get("top_k", 5)), 20)
        results = []
        if query:
            try:
                client = _get_chroma_client()
                col = client.get_collection(name=collection_name)
                doc_count = col.count()
                if doc_count > 0:
                    n = min(top_k, doc_count)
                    raw = col.query(
                        query_texts=[query],
                        n_results=n,
                        include=["documents", "metadatas", "distances"],
                    )
                    docs = raw["documents"][0] if raw["documents"] else []
                    metas = raw["metadatas"][0] if raw["metadatas"] else []
                    dists = raw["distances"][0] if raw["distances"] else []
                    ids = raw["ids"][0] if raw["ids"] else []
                    for doc, meta, dist, doc_id in zip(
                        docs, metas, dists, ids,
                    ):
                        score = max(0.0, 1.0 - dist)
                        text = doc[:300] + "..." if len(doc) > 300 else doc
                        results.append({
                            "id": doc_id,
                            "score": score,
                            "text": text,
                            "metadata": meta or {},
                        })
            except Exception as e:
                logger.debug("RAG search query: %s", e)
        tmpl = _templates.get_template("partials/rag_results.html")
        return _set_ui_cookie(HTMLResponse(tmpl.render(
            results=results,
            query=query,
        )))

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
        except Exception as e:
            logger.debug("CPU metrics: %s", e)
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
