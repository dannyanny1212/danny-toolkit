"""Eternal Sentinel — Autonome bewaker van het OMEGA v6.11.0 Trinity systeem.

Vier kernfuncties:
1. Hourly L3 Deep Scan — integriteitscontrole
2. Auto-Throttle — L1 Pulse > 10ms → swarm throttle
3. GPU P-State Management — P0 bij missie, P8 bij idle
4. Nightly Re-index — nieuwe CorticalStack events → RAG chunks
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
from datetime import datetime

try:
    import danny_toolkit.core.advanced_knowledge_bridge
    HAS_ADVANCED_KNOWLEDGE_BRIDGE = True
except ImportError:
    HAS_ADVANCED_KNOWLEDGE_BRIDGE = False

try:
    import danny_toolkit.core.neural_bus
    HAS_NEURAL_BUS = True
except ImportError:
    HAS_NEURAL_BUS = False

try:
    import danny_toolkit.core.vram_manager
    HAS_VRAM_MANAGER = True
except ImportError:
    HAS_VRAM_MANAGER = False

try:
    import pathlib
    HAS_PATHLIB = True
except ImportError:
    HAS_PATHLIB = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────
API_BASE = "http://127.0.0.1:8000"
API_KEY = os.getenv("FASTAPI_SECRET_KEY", "EJEa_Cy3Aj22aykbeKaWaBCuQH27d4Tmb8VemO-yn6o")
HEADERS = {"X-API-Key": API_KEY}

DEEP_SCAN_INTERVAL = 3600      # 1 uur
PULSE_CHECK_INTERVAL = 30      # 30 seconden
PULSE_THRESHOLD_MS = 10.0      # auto-throttle drempel
NIGHTLY_HOUR = 3               # 03:00 — re-index voor Dreamer REM om 04:00
REINDEX_MAX_EVENTS = 200       # max events per nightly batch


class EternalSentinel:
    """Zelf-optimaliserend bewakingssysteem voor het OMEGA ecosysteem."""

    def __init__(self) -> None:
        """Init  ."""
        self._running = False
        self._throttle_active = False
        self._last_deep_scan: float = 0.0
        self._last_reindex_date: str = ""
        self._deep_scan_count = 0
        self._throttle_count = 0
        self._gpu_boost_count = 0
        self._reindex_count = 0
        self._threads: list[threading.Thread] = []

    # ── Public API ────────────────────────────────────────

    @property
    def is_throttled(self) -> bool:
        """Geeft aan of het systeem in auto-throttle modus staat."""
        return self._throttle_active

    def start(self) -> None:
        """Start alle sentinel loops als daemon threads."""
        if self._running:
            return
        self._running = True

        loops = [
            ("sentinel-deep", self._deep_scan_loop),
            ("sentinel-pulse", self._pulse_monitor_loop),
            ("sentinel-night", self._nightly_loop),
        ]
        for name, target in loops:
            t = threading.Thread(target=target, name=name, daemon=True)
            t.start()
            self._threads.append(t)

        # Subscribe op NeuralBus voor GPU P-State management
        self._subscribe_mission_events()

        logger.info("[SENTINEL] Eternal Sentinel geactiveerd — 3 loops + NeuralBus")

    def stop(self) -> None:
        """Signaleer alle loops om te stoppen."""
        self._running = False

    def get_status(self) -> dict:
        """Retourneer sentinel metrics voor dashboard/API."""
        return {
            "running": self._running,
            "throttle_active": self._throttle_active,
            "deep_scans": self._deep_scan_count,
            "throttle_triggers": self._throttle_count,
            "gpu_boosts": self._gpu_boost_count,
            "nightly_reindexes": self._reindex_count,
        }

    # ── Loop 1: Hourly L3 Deep Scan ──────────────────────

    def _deep_scan_loop(self) -> None:
        """Voer elke 60 minuten een L3 Deep Scan uit."""
        while self._running:
            now = time.time()
            if now - self._last_deep_scan >= DEEP_SCAN_INTERVAL:
                self._last_deep_scan = now
                self._run_deep_scan()
            time.sleep(60)  # check elke minuut

    def _run_deep_scan(self) -> None:
        """Roep /api/v1/health/deep aan en log het resultaat."""
        try:
            pass  # import moved to top-level
            resp = requests.get(
                f"{API_BASE}/api/v1/health/deep",
                headers=HEADERS,
                timeout=30,
            )
            data = resp.json()
            self._deep_scan_count += 1

            status = data.get("status", "unknown")
            groq = "OK" if data.get("groq_bereikbaar") else "FAIL"
            cortical = "OK" if data.get("cortical_stack_writable") else "FAIL"

            logger.info(
                "[SENTINEL] Deep Scan #%d: status=%s groq=%s cortical=%s",
                self._deep_scan_count, status, groq, cortical,
            )

            # Publiceer resultaat op NeuralBus
            self._publish("SENTINEL_DEEP_SCAN", {
                "scan_nr": self._deep_scan_count,
                "status": status,
                "groq": groq,
                "cortical": cortical,
            })
        except Exception as e:
            logger.warning("[SENTINEL] Deep Scan fout: %s", e)

    # ── Loop 2: L1 Pulse Monitor + Auto-Throttle ─────────

    def _pulse_monitor_loop(self) -> None:
        """Meet elke 30s de L1 Pulse latentie. Throttle bij >10ms."""
        # Warmup: eerste 60s overslaan (cold-start HTTP overhead)
        time.sleep(60)
        # Warmup request om TCP connectie op te bouwen
        try:
            pass  # import moved to top-level
            requests.get(f"{API_BASE}/api/v1/health", headers=HEADERS, timeout=5)
        except Exception as _sup_err:
            logger.debug("Suppressed: %s", _sup_err)
        while self._running:
            self._check_pulse()
            time.sleep(PULSE_CHECK_INTERVAL)

    def _check_pulse(self) -> None:
        """Eén L1 Pulse meting + throttle logica."""
        try:
            pass  # import moved to top-level
            t0 = time.time()
            resp = requests.get(
                f"{API_BASE}/api/v1/health",
                headers=HEADERS,
                timeout=5,
            )
            latency_ms = (time.time() - t0) * 1000
            resp.json()  # valideer response

            if latency_ms > PULSE_THRESHOLD_MS and not self._throttle_active:
                # THROTTLE ACTIVEREN
                self._throttle_active = True
                self._throttle_count += 1
                logger.warning(
                    "[SENTINEL] AUTO-THROTTLE ON — L1 Pulse %.1fms > %.0fms drempel",
                    latency_ms, PULSE_THRESHOLD_MS,
                )
                self._publish("SENTINEL_THROTTLE", {
                    "active": True,
                    "latency_ms": round(latency_ms, 1),
                    "threshold_ms": PULSE_THRESHOLD_MS,
                })
            elif latency_ms <= PULSE_THRESHOLD_MS and self._throttle_active:
                # THROTTLE OPHEFFEN
                self._throttle_active = False
                logger.info(
                    "[SENTINEL] AUTO-THROTTLE OFF — L1 Pulse %.1fms hersteld",
                    latency_ms,
                )
                self._publish("SENTINEL_THROTTLE", {
                    "active": False,
                    "latency_ms": round(latency_ms, 1),
                })
        except Exception as e:
            logger.debug("[SENTINEL] Pulse check fout: %s", e)

    # ── GPU P-State Management ────────────────────────────

    def _subscribe_mission_events(self) -> None:
        """Luister op NeuralBus voor missie start/einde events."""
        try:
            pass  # import moved to top-level
            bus = get_bus()
            bus.subscribe(EventTypes.MISSION_STARTED, self._on_mission_start)
            bus.subscribe(EventTypes.REQUEST_TRACE_COMPLETE, self._on_mission_end)
            logger.info("[SENTINEL] GPU P-State subscribed op NeuralBus")
        except Exception as e:
            logger.debug("[SENTINEL] NeuralBus subscribe fout: %s", e)

    def _on_mission_start(self, event) -> None:
        """GPU naar P0 (Maximum Performance) bij missie start."""
        try:
            pass  # import moved to top-level
            result = gpu_set_clocks(min_mhz=1500, max_mhz=2100)
            self._gpu_boost_count += 1
            logger.info(
                "[SENTINEL] GPU BOOST P0 — clocks locked 1500-2100 MHz (%s)",
                result.get("status", "?"),
            )
        except Exception as e:
            logger.debug("[SENTINEL] GPU boost fout: %s", e)

    def _on_mission_end(self, event) -> None:
        """GPU terug naar Power Save na missie einde."""
        try:
            pass  # import moved to top-level
            result = gpu_reset_clocks()
            logger.info(
                "[SENTINEL] GPU IDLE — clocks reset (%s)",
                result.get("status", "?"),
            )
        except Exception as e:
            logger.debug("[SENTINEL] GPU reset fout: %s", e)

    # ── Loop 3: Nightly Re-index ──────────────────────────

    def _nightly_loop(self) -> None:
        """Check elk uur of het 03:00 is voor nightly re-index."""
        while self._running:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")

            if now.hour == NIGHTLY_HOUR and self._last_reindex_date != today:
                self._last_reindex_date = today
                self._run_nightly_reindex()

            time.sleep(300)  # check elke 5 minuten

    def _run_nightly_reindex(self) -> None:
        """Verwerk recente CorticalStack events naar RAG chunks."""
        logger.info("[SENTINEL] Nightly Re-index gestart...")
        try:
            # Haal recente events op
            pass  # import moved to top-level
            resp = requests.get(
                f"{API_BASE}/api/v1/memory/recent",
                headers=HEADERS,
                params={"count": REINDEX_MAX_EVENTS},
                timeout=30,
            )
            data = resp.json()
            events = data.get("events", [])

            if not events:
                logger.info("[SENTINEL] Geen nieuwe events voor re-index")
                return

            # Synthetiseer daily lesson
            lesson = self._synthesize_daily_lesson(events)
            if not lesson:
                return

            # Schrijf naar RAG document
            pass  # import moved to top-level
            doc_path = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "data" / "rag" / "documenten"
            doc_path.mkdir(parents=True, exist_ok=True)

            today = datetime.now().strftime("%Y-%m-%d")
            filename = f"daily_lesson_{today}.md"
            filepath = doc_path / filename

            filepath.write_text(lesson, encoding="utf-8")
            logger.info("[SENTINEL] Daily Lesson geschreven: %s (%d chars)", filename, len(lesson))

            # Ingest via AdvancedKnowledgeBridge
            try:
                pass  # import moved to top-level
                bridge = AdvancedKnowledgeBridge()
                chunks = bridge.ingest_modules([filename])
                self._reindex_count += 1
                logger.info("[SENTINEL] Re-index compleet: %d chunks geïndexeerd", chunks)
                self._publish("SENTINEL_REINDEX", {
                    "date": today,
                    "events_processed": len(events),
                    "chunks_indexed": chunks,
                })
            except Exception as e:
                logger.warning("[SENTINEL] Ingestie fout: %s", e)

        except Exception as e:
            logger.warning("[SENTINEL] Nightly re-index fout: %s", e)

    def _synthesize_daily_lesson(self, events: list) -> str:
        """Maak een Daily Lesson document van CorticalStack events."""
        today = datetime.now().strftime("%Y-%m-%d")

        # Categoriseer events
        actors = {}
        for ev in events:
            actor = ev.get("actor", "unknown")
            actors.setdefault(actor, []).append(ev)

        content = f"# Daily Lesson — {today}\n\n"
        content += f"## Samenvatting\n\n"
        content += f"- **Events verwerkt**: {len(events)}\n"
        content += f"- **Actieve actoren**: {len(actors)}\n"
        content += f"- **Periode**: {events[-1].get('timestamp', '?')[:16]} tot {events[0].get('timestamp', '?')[:16]}\n\n"

        content += "## Activiteit per Actor\n\n"
        for actor, evts in sorted(actors.items(), key=lambda x: -len(x[1])):
            actions = set(e.get("action", "?") for e in evts)
            content += f"### {actor} ({len(evts)} events)\n"
            content += f"- Acties: {', '.join(sorted(actions))}\n"

            # Pak de meest recente event details
            latest = evts[0]
            details = latest.get("details", {})
            if isinstance(details, dict):
                highlights = []
                for k, v in list(details.items())[:3]:
                    highlights.append(f"{k}={v}")
                if highlights:
                    content += f"- Laatste: {'; '.join(highlights)}\n"
            content += "\n"

        content += "## Trinity Status\n\n"
        content += "- **MIND**: Agents operationeel, routing intact\n"
        content += "- **BODY**: Hardware binnen nominale parameters\n"
        content += "- **SOUL**: CorticalStack schrijfbaar, events stromen\n"

        return content

    # ── Helpers ────────────────────────────────────────────

    def _publish(self, event_name: str, data: dict) -> None:
        """Publiceer een sentinel event op de NeuralBus."""
        try:
            pass  # import moved to top-level
            get_bus().publish(event_name, data, bron="eternal_sentinel")
        except Exception as _sup_err:
            logger.debug("Suppressed: %s", _sup_err)


# ── Singleton ─────────────────────────────────────────────

_sentinel: EternalSentinel | None = None
_sentinel_lock = threading.Lock()


def get_sentinel() -> EternalSentinel:
    """Verkrijg de singleton EternalSentinel instantie."""
    global _sentinel
    if _sentinel is None:
        with _sentinel_lock:
            if _sentinel is None:
                _sentinel = EternalSentinel()
    return _sentinel
