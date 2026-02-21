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
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
        return _stream_response(req.message, brain)

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


def _stream_response(message: str, brain):
    """SSE streaming generator voor live updates."""
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

        # Stuur callback updates als SSE events
        for update in updates:
            yield (
                f"data: {json.dumps({'update': update})}"
                "\n\n"
            )

        # Stuur uiteindelijke payloads
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

    # Wrap async generator in sync generator
    async def _run():
        results = []
        async for chunk in _generate():
            results.append(chunk)
        return results

    loop = asyncio.new_event_loop()
    chunks = loop.run_until_complete(_run())
    loop.close()

    def _sync_gen():
        for chunk in chunks:
            yield chunk

    return StreamingResponse(
        _sync_gen(),
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
