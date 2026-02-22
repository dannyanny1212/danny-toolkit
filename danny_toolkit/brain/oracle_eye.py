import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_STACK = True
except ImportError:
    HAS_STACK = False

try:
    from danny_toolkit.core.neural_bus import get_bus, EventTypes
    HAS_BUS = True
except ImportError:
    HAS_BUS = False


@dataclass
class HourForecast:
    """Voorspelling voor een specifiek uur."""
    uur: int
    verwachte_queries: float
    verwachte_cpu: float
    verwachte_ram: float
    aanbevolen_model: str
    confidence: float


class TheOracleEye:
    """
    THE ORACLE EYE (Invention #18)
    ------------------------------
    Predictieve resource scaler.

    Analyseert historische patronen uit CorticalStack om
    toekomstige systeembelasting te voorspellen. Adviseert
    model-keuze (70B vs 8B) op basis van verwachte load.

    Pure statistiek — geen ML, geen extra dependencies.
    CPU-vriendelijk via rolling averages over uur-buckets.

    Features:
    - Uurpatroon-analyse over N dagen
    - Forecast voor komende uren
    - Piekuur detectie
    - Pre-warm advies
    - Model-selectie advies (advisory only)
    - NeuralBus publicatie van forecasts
    """

    # Model selectie drempels
    _HIGH_CPU_THRESHOLD = 70.0      # % CPU → switch naar 8B
    _HIGH_QUERY_THRESHOLD = 50      # queries/uur → switch naar 8B
    _CACHE_TTL = 300                # 5 minuten cache

    def __init__(self):
        self._stack = get_cortical_stack() if HAS_STACK else None
        self._bus = get_bus() if HAS_BUS else None
        self._cache: Dict[str, tuple] = {}  # key -> (timestamp, data)

    def _get_cached(self, key: str):
        """Haal gecachte waarde op als TTL niet verlopen."""
        if key in self._cache:
            ts, data = self._cache[key]
            if time.time() - ts < self._CACHE_TTL:
                return data
        return None

    def _set_cached(self, key: str, data):
        """Sla waarde op in cache."""
        self._cache[key] = (time.time(), data)

    def analyze_patterns(self, days: int = 7) -> Dict:
        """
        Aggregeer system_stats + episodic_memory per uur-van-de-dag.

        Returns:
            Dict met hour (0-23) -> {avg_queries, avg_cpu, avg_ram, sample_count}
        """
        cached = self._get_cached(f"patterns_{days}")
        if cached:
            return cached

        if not self._stack:
            return {}

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        hourly = defaultdict(lambda: {
            "queries": [], "cpu": [], "ram": [],
        })

        try:
            # Episodic events — tel queries per uur
            events = self._stack._conn.execute("""
                SELECT timestamp FROM episodic_memory
                WHERE timestamp >= ?
            """, (cutoff,)).fetchall()

            for row in events:
                try:
                    ts = datetime.fromisoformat(row[0])
                    hourly[ts.hour]["queries"].append(1)
                except (ValueError, TypeError):
                    continue

            # System stats — CPU en RAM per uur
            stats = self._stack._conn.execute("""
                SELECT timestamp, metric, value FROM system_stats
                WHERE timestamp >= ?
                AND metric IN ('cpu_percent', 'ram_percent')
            """, (cutoff,)).fetchall()

            for row in stats:
                try:
                    ts = datetime.fromisoformat(row[0])
                    metric = row[1]
                    value = float(row[2])
                    if metric == "cpu_percent":
                        hourly[ts.hour]["cpu"].append(value)
                    elif metric == "ram_percent":
                        hourly[ts.hour]["ram"].append(value)
                except (ValueError, TypeError):
                    continue

        except Exception as e:
            print(f"{Kleur.ROOD}[OracleEye] Analyse-fout: {e}{Kleur.RESET}")
            return {}

        # Bereken gemiddelden per uur
        result = {}
        for hour in range(24):
            data = hourly[hour]
            q = data["queries"]
            c = data["cpu"]
            r = data["ram"]
            result[hour] = {
                "avg_queries": sum(q) / max(len(q), 1) * (len(q) / max(days, 1)),
                "avg_cpu": sum(c) / max(len(c), 1) if c else 0.0,
                "avg_ram": sum(r) / max(len(r), 1) if r else 0.0,
                "sample_count": len(q) + len(c) + len(r),
            }

        self._set_cached(f"patterns_{days}", result)
        return result

    def forecast_next_hours(self, hours: int = 4) -> List[HourForecast]:
        """Voorspel CPU/RAM/queries voor de komende uren."""
        patterns = self.analyze_patterns()
        if not patterns:
            return []

        now_hour = datetime.now().hour
        forecasts = []

        for offset in range(1, hours + 1):
            target_hour = (now_hour + offset) % 24
            data = patterns.get(target_hour, {})

            avg_cpu = data.get("avg_cpu", 0.0)
            avg_queries = data.get("avg_queries", 0.0)
            avg_ram = data.get("avg_ram", 0.0)
            samples = data.get("sample_count", 0)

            # Confidence gebaseerd op hoeveelheid data
            confidence = min(0.9, samples / 50.0) if samples > 0 else 0.1

            model = self._kies_model(avg_cpu, avg_queries)

            forecasts.append(HourForecast(
                uur=target_hour,
                verwachte_queries=round(avg_queries, 1),
                verwachte_cpu=round(avg_cpu, 1),
                verwachte_ram=round(avg_ram, 1),
                aanbevolen_model=model,
                confidence=round(confidence, 2),
            ))

        return forecasts

    def _kies_model(
        self,
        verwachte_cpu: float,
        verwachte_queries: float,
    ) -> str:
        """Kies 70B vs 8B op basis van verwachte belasting."""
        if (
            verwachte_cpu > self._HIGH_CPU_THRESHOLD
            or verwachte_queries > self._HIGH_QUERY_THRESHOLD
        ):
            return Config.LLM_FALLBACK_MODEL
        return Config.LLM_MODEL

    def suggest_model(
        self,
        current_load: Dict,
        forecast: Optional[List[HourForecast]] = None,
    ) -> str:
        """
        Adviseer model op basis van huidige staat + forecast.

        Args:
            current_load: {"cpu": float, "ram": float, "queries_last_hour": int}
            forecast: Optionele forecast (wordt berekend als None)

        Returns:
            Model naam (advisory only)
        """
        cpu = current_load.get("cpu", 0.0)
        queries = current_load.get("queries_last_hour", 0)

        # Als huidige load al hoog is, direct fallback
        if cpu > self._HIGH_CPU_THRESHOLD or queries > self._HIGH_QUERY_THRESHOLD:
            return Config.LLM_FALLBACK_MODEL

        # Check forecast — als piek verwacht, preventief fallback
        if forecast is None:
            forecast = self.forecast_next_hours(hours=2)

        for fc in forecast:
            if (
                fc.confidence > 0.3
                and (
                    fc.verwachte_cpu > self._HIGH_CPU_THRESHOLD
                    or fc.verwachte_queries > self._HIGH_QUERY_THRESHOLD
                )
            ):
                return Config.LLM_FALLBACK_MODEL

        return Config.LLM_MODEL

    def get_peak_hours(self, days: int = 7) -> List[int]:
        """Top 5 uren met meeste activiteit."""
        patterns = self.analyze_patterns(days=days)
        if not patterns:
            return []

        sorted_hours = sorted(
            patterns.items(),
            key=lambda x: x[1].get("sample_count", 0),
            reverse=True,
        )
        return [h for h, _ in sorted_hours[:5]]

    def pre_warm_check(self) -> Optional[str]:
        """
        Check of er een piek verwacht wordt binnen 2 uur.

        Returns:
            Advies-string als piek verwacht, anders None.
        """
        forecasts = self.forecast_next_hours(hours=2)
        if not forecasts:
            return None

        for fc in forecasts:
            if fc.confidence < 0.2:
                continue
            if (
                fc.verwachte_cpu > self._HIGH_CPU_THRESHOLD
                or fc.verwachte_queries > self._HIGH_QUERY_THRESHOLD
            ):
                return (
                    f"Piek verwacht om {fc.uur:02d}:00 — "
                    f"CPU: {fc.verwachte_cpu:.0f}%, "
                    f"Queries: {fc.verwachte_queries:.0f}/uur. "
                    f"Aanbevolen: {fc.aanbevolen_model}"
                )

        return None

    def generate_daily_forecast(self) -> str:
        """
        Genereer een leesbare dagelijkse forecast.

        Publiceert naar NeuralBus en logt naar CorticalStack.

        Returns:
            Forecast als leesbare string.
        """
        forecasts = self.forecast_next_hours(hours=12)
        peaks = self.get_peak_hours()

        lines = ["[ORACLE EYE — Dagelijkse Forecast]"]
        lines.append(f"Gegenereerd: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        if peaks:
            peak_str = ", ".join(f"{h:02d}:00" for h in peaks)
            lines.append(f"Piekuren (afgelopen week): {peak_str}")
            lines.append("")

        if forecasts:
            lines.append("Komende uren:")
            for fc in forecasts:
                indicator = "🔴" if fc.aanbevolen_model.endswith("qwen3-32b") else "🟢"
                lines.append(
                    f"  {indicator} {fc.uur:02d}:00 — "
                    f"CPU: {fc.verwachte_cpu:.0f}%, "
                    f"RAM: {fc.verwachte_ram:.0f}%, "
                    f"Queries: {fc.verwachte_queries:.0f}/uur "
                    f"[{fc.aanbevolen_model.split('/')[-1]}] "
                    f"(conf: {fc.confidence:.0%})"
                )
        else:
            lines.append("Onvoldoende data voor forecast.")

        forecast_text = "\n".join(lines)

        # Publiceer naar NeuralBus
        if self._bus and HAS_BUS:
            try:
                self._bus.publish(
                    EventTypes.RESOURCE_FORECAST,
                    {
                        "forecast": forecast_text,
                        "peak_hours": peaks,
                        "hours_ahead": len(forecasts),
                    },
                    bron="oracle_eye",
                )
            except Exception as e:
                logger.debug("NeuralBus publish error: %s", e)

        # Log naar CorticalStack
        if self._stack:
            try:
                self._stack.log_event(
                    actor="oracle_eye",
                    action="daily_forecast",
                    details={
                        "peak_hours": peaks,
                        "forecast_hours": len(forecasts),
                    },
                    source="oracle_eye",
                )
                self._stack.flush()
            except Exception as e:
                logger.debug("CorticalStack log error: %s", e)

        return forecast_text
