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
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
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
    response: Response,
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
        except Exception as e:
            logger.debug("Governor stats: %s", e)
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
        except Exception as e:
            logger.debug("Rate limits: %s", e)
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
        except Exception as e:
            logger.debug("Cortex stats: %s", e)
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

    @app.get("/ui/partials/observatory", response_class=HTMLResponse, include_in_schema=False)
    async def partial_observatory():
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
        return HTMLResponse(tmpl.render(dashboard=dashboard_data))

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
                except Exception as e:
                    logger.debug("SSE event: %s", e)
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
