"""
RequestTracer — Distributed tracing voor de SwarmEngine pipeline.

Volgt een request door alle pipeline-fases: routing, memex, dispatch,
tribunal, sentinel, schild. Gebruikt contextvars voor per-request state.

Singleton via get_request_tracer().

Gebruik:
    from danny_toolkit.core.request_tracer import get_request_tracer

    tracer = get_request_tracer()
    trace = tracer.begin_trace("a1b2c3d4")
    span = tracer.begin_span("routing")
    tracer.eind_span("ok")
    tracer.eind_trace()
"""

from __future__ import annotations

import contextvars
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─── ContextVar voor per-request state ───────────────

_current_trace: contextvars.ContextVar[Optional["RequestTrace"]] = (
    contextvars.ContextVar("current_trace", default=None)
)
_current_span: contextvars.ContextVar[Optional["TraceSpan"]] = (
    contextvars.ContextVar("current_span", default=None)
)


# ─── Dataclasses ─────────────────────────────────────

@dataclass
class TraceSpan:
    """Eén fase in de pipeline trace."""
    trace_id: str
    fase: str               # "routing", "memex", "dispatch:AgentName", etc.
    agent: str = ""
    start_ms: float = 0.0
    eind_ms: float = 0.0
    status: str = "pending"  # "pending", "ok", "error", "skipped"
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Returns the duration in milliseconds. 
 Calculates the difference between `eind_ms` and `start_ms` if both are positive, 
 otherwise returns 0.0. 
 Returns: float, duration in milliseconds, rounded to 2 decimal places."""
        if self.eind_ms > 0 and self.start_ms > 0:
            """Calculates the duration in milliseconds between the start and end times. 
Returns 0.0 if either start or end time is not set. 
The result is rounded to two decimal places."""
            return round(self.eind_ms - self.start_ms, 2)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "fase": self.fase,
            "agent": self.agent,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "details": self.details,
        }


@dataclass
class RequestTrace:
    """Volledige trace van een request door de pipeline."""
    trace_id: str
    start: float = field(default_factory=lambda: time.time() * 1000)
    spans: List[TraceSpan] = field(default_factory=list)
    fout_ids: List[str] = field(default_factory=list)  # fout_id referenties
    afgerond: bool = False

    @property
    def duration_ms(self) -> float:
        """Duration ms."""
        if self.spans:
            eind = max(
                (s.eind_ms for s in self.spans if s.eind_ms > 0),
                default=self.start,
            )
            return round(eind - self.start, 2)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "trace_id": self.trace_id,
            "start": self.start,
            "duration_ms": self.duration_ms,
            "spans": [s.to_dict() for s in self.spans],
            "fouten": self.fout_ids,
            "afgerond": self.afgerond,
        }

    def to_summary(self) -> Dict[str, Any]:
        """Compacte samenvatting voor lijstweergave."""
        return {
            "trace_id": self.trace_id,
            "duration_ms": self.duration_ms,
            "span_count": len(self.spans),
            "error_count": len(self.fout_ids),
            "status": "error" if self.fout_ids else "ok",
        }


# ═══════════════════════════════════════════════════════
# RequestTracer
# ═══════════════════════════════════════════════════════

class RequestTracer:
    """Per-request lifecycle tracker.

    Slaat traces op in een in-memory ringbuffer (deque).
    Optioneel persistent naar CorticalStack.
    """

    _MAX_TRACES = 200

    def __init__(self) -> None:
        """Initializes the object, setting up synchronization and data structures to manage request traces.

 * Acquires a lock (`self._lock`) for thread-safe operations.
 * Creates a deque (`self._traces`) with a maximum size (`self._MAX_TRACES`) to store recent request traces.
 * Initializes an index (`self._index`) to map request identifiers to their corresponding traces."""
        self._lock = threading.Lock()
        self._traces: Deque[RequestTrace] = deque(maxlen=self._MAX_TRACES)
        self._index: Dict[str, RequestTrace] = {}  # trace_id -> trace

    def begin_trace(self, trace_id: str) -> RequestTrace:
        """Start een nieuwe request trace.

        Args:
            trace_id: Uniek 8-char hex trace ID.

        Returns:
            Nieuwe RequestTrace instantie.
        """
        try:
            trace = RequestTrace(trace_id=trace_id)
            _current_trace.set(trace)

            with self._lock:
                self._traces.append(trace)
                self._index[trace_id] = trace
                # Schoon index op bij overflow
                if len(self._index) > self._MAX_TRACES:
                    stale = list(self._index.keys())[:-self._MAX_TRACES]
                    for k in stale:
                        self._index.pop(k, None)

            return trace
        except Exception as e:
            logger.debug("RequestTracer begin_trace fout: %s", e)
            return RequestTrace(trace_id=trace_id)

    def begin_span(
        self, fase: str, agent: str = "",
    ) -> Optional[TraceSpan]:
        """Start een nieuwe span binnen de huidige trace.

        Args:
            fase: Pipeline fase naam ("routing", "memex", etc.).
            agent: Optionele agent naam.

        Returns:
            TraceSpan of None als geen actieve trace.
        """
        try:
            trace = _current_trace.get()
            if trace is None:
                return None

            span = TraceSpan(
                trace_id=trace.trace_id,
                fase=fase,
                agent=agent,
                start_ms=time.time() * 1000,
            )
            trace.spans.append(span)
            _current_span.set(span)
            return span
        except Exception as e:
            logger.debug("RequestTracer begin_span fout: %s", e)
            return None

    def eind_span(
        self,
        status: str = "ok",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Sluit de huidige span.

        Args:
            status: "ok", "error", of "skipped".
            details: Extra details voor de span.
        """
        try:
            span = _current_span.get()
            if span is None:
                return

            span.eind_ms = time.time() * 1000
            span.status = status
            if details:
                span.details.update(details)
            _current_span.set(None)
        except Exception as e:
            logger.debug("RequestTracer eind_span fout: %s", e)

    def registreer_fout(self, fout_id: str) -> None:
        """Registreer een fout-ID in de huidige trace.

        Args:
            fout_id: FoutContext.fout_id referentie.
        """
        try:
            trace = _current_trace.get()
            if trace is not None:
                trace.fout_ids.append(fout_id)
        except Exception as e:
            logger.debug("RequestTracer registreer_fout fout: %s", e)

    def eind_trace(self) -> Optional[RequestTrace]:
        """Sluit de huidige trace en log naar CorticalStack.

        Returns:
            Afgeronde RequestTrace of None.
        """
        trace = _current_trace.get()
        if trace is None:
            return None

        trace.afgerond = True
        _current_trace.set(None)
        _current_span.set(None)

        # NeuralBus event
        try:
            from danny_toolkit.core.neural_bus import (
                get_bus, EventTypes,
            )
            bus = get_bus()
            bus.publish(
                EventTypes.REQUEST_TRACE_COMPLETE,
                {
                    "trace_id": trace.trace_id,
                    "duration_ms": trace.duration_ms,
                    "span_count": len(trace.spans),
                    "error_count": len(trace.fout_ids),
                },
                bron="RequestTracer",
            )
        except Exception as e:
            logger.debug("RequestTracer NeuralBus fout: %s", e)

        # CorticalStack logging
        from danny_toolkit.core.memory_interface import log_to_cortical
        log_to_cortical(
            actor="RequestTracer",
            action="trace_complete",
            details={
                "trace_id": trace.trace_id,
                "duration_ms": trace.duration_ms,
                "spans": len(trace.spans),
                "fouten": len(trace.fout_ids),
            },
        )

        return trace

    def get_trace(self, trace_id: str) -> Optional[RequestTrace]:
        """Haal een trace op via ID.

        Args:
            trace_id: 8-char hex trace ID.

        Returns:
            RequestTrace of None.
        """
        try:
            with self._lock:
                return self._index.get(trace_id)
        except Exception as e:
            logger.debug("RequestTracer get_trace fout: %s", e)
            return None

    def get_recent(self, count: int = 20) -> List[RequestTrace]:
        """Haal recente traces op.

        Args:
            count: Maximum aantal traces.

        Returns:
            Lijst van RequestTrace (nieuwste eerst).
        """
        try:
            with self._lock:
                traces = list(self._traces)
            return list(reversed(traces[-count:]))
        except Exception as e:
            logger.debug("RequestTracer get_recent fout: %s", e)
            return []


# ─── Singleton ───────────────────────────────────────

_tracer_instance: Optional[RequestTracer] = None
_tracer_lock = threading.Lock()


def get_request_tracer() -> RequestTracer:
    """Verkrijg de singleton RequestTracer instantie."""
    global _tracer_instance
    if _tracer_instance is None:
        with _tracer_lock:
            if _tracer_instance is None:
                _tracer_instance = RequestTracer()
    return _tracer_instance
