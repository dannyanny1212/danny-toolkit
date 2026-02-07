"""
PerformanceAnalyzer - Tracking en analyse van systeem performance.

Dit systeem meet en analyseert de performance van alle componenten
om trends te identificeren en verbeterpunten te vinden.

AUTHOR: Danny Toolkit
DATE: 7 februari 2026
"""

import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

try:
    from ..core.config import Config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False


@dataclass
class PerformanceMetric:
    """Een enkele performance metric."""
    timestamp: str
    metric_type: str  # "workflow", "response", "daemon", "learning"
    name: str
    value: float
    context: dict


class PerformanceAnalyzer:
    """
    Analyseert systeem performance voor self-improvement.

    Tracked metrics over tijd en identificeert trends,
    verbeteringen en probleemgebieden.
    """

    MAX_METRICS = 1000
    TREND_WINDOW = 50  # Aantal datapunten voor trend analyse

    def __init__(self, data_dir: Path = None):
        if data_dir is None and HAS_CONFIG:
            data_dir = Config.APPS_DATA_DIR
        elif data_dir is None:
            data_dir = Path("data/apps")

        self.data_dir = data_dir
        self.metrics_file = data_dir / "performance_metrics.json"
        self._data = self._load()

    def _load(self) -> dict:
        """Laad metrics data uit bestand."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return {
            "metrics": [],
            "trends": {},
            "baselines": {},
            "improvements": [],
            "created": datetime.now().isoformat(),
            "last_update": None
        }

    def save(self):
        """Sla metrics data op naar bestand."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._data["last_update"] = datetime.now().isoformat()
        with open(self.metrics_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def record(
        self,
        metric_type: str,
        name: str,
        value: float,
        context: dict = None
    ):
        """
        Registreer een performance metric.

        Args:
            metric_type: Type metric (workflow, response, daemon, learning)
            name: Naam van de metric
            value: Waarde (meestal 0-1 of tijd in ms)
            context: Optionele extra context
        """
        metric = PerformanceMetric(
            timestamp=datetime.now().isoformat(),
            metric_type=metric_type,
            name=name,
            value=value,
            context=context or {}
        )
        self._data["metrics"].append(asdict(metric))

        # Keep last MAX_METRICS metrics
        if len(self._data["metrics"]) > self.MAX_METRICS:
            self._data["metrics"] = self._data["metrics"][-self.MAX_METRICS:]

        self._update_trends(metric_type, name, value)
        self.save()

    def _update_trends(self, metric_type: str, name: str, value: float):
        """Update trend data voor een metric."""
        key = f"{metric_type}:{name}"

        if key not in self._data["trends"]:
            self._data["trends"][key] = {
                "values": [],
                "avg": 0.0,
                "min": value,
                "max": value,
                "improving": False,
                "improvement_rate": 0.0
            }

        trend = self._data["trends"][key]
        trend["values"].append(value)

        # Keep last TREND_WINDOW values for trend
        if len(trend["values"]) > self.TREND_WINDOW:
            trend["values"] = trend["values"][-self.TREND_WINDOW:]

        values = trend["values"]
        trend["avg"] = statistics.mean(values)
        trend["min"] = min(values)
        trend["max"] = max(values)

        # Check if improving (last 10 vs first 10)
        if len(values) >= 20:
            first_half = statistics.mean(values[:10])
            last_half = statistics.mean(values[-10:])

            if first_half > 0:
                improvement_rate = (last_half - first_half) / first_half
                trend["improvement_rate"] = improvement_rate
                # For most metrics, higher is better
                trend["improving"] = improvement_rate > 0.05

    def get_trend(self, metric_type: str, name: str) -> Optional[dict]:
        """Haal trend op voor een specifieke metric."""
        key = f"{metric_type}:{name}"
        return self._data["trends"].get(key)

    def get_all_trends(self) -> dict:
        """Haal alle trends op."""
        return self._data["trends"].copy()

    def get_improvement_rate(self) -> float:
        """Bereken overall improvement rate."""
        trends = self._data["trends"]
        if not trends:
            return 0.0

        improving = sum(
            1 for t in trends.values()
            if t.get("improving", False)
        )
        return improving / len(trends)

    def get_learning_summary(self) -> dict:
        """Genereer samenvatting van learning progress."""
        return {
            "total_metrics": len(self._data["metrics"]),
            "tracked_trends": len(self._data["trends"]),
            "improvement_rate": self.get_improvement_rate(),
            "top_improvements": self._get_top_improvements(),
            "areas_needing_work": self._get_problem_areas(),
            "last_update": self._data.get("last_update")
        }

    def _get_top_improvements(self, limit: int = 5) -> List[dict]:
        """Vind metrics met meeste verbetering."""
        improvements = []

        for key, trend in self._data["trends"].items():
            if len(trend["values"]) >= 10:
                first = statistics.mean(trend["values"][:5])
                last = statistics.mean(trend["values"][-5:])

                if first > 0:
                    improvement = (last - first) / first
                    improvements.append({
                        "metric": key,
                        "improvement": round(improvement, 3),
                        "current": round(last, 3),
                        "previous": round(first, 3)
                    })

        improvements.sort(key=lambda x: x["improvement"], reverse=True)
        return improvements[:limit]

    def _get_problem_areas(self, limit: int = 5) -> List[dict]:
        """Vind metrics die achteruitgaan."""
        problems = []

        for key, trend in self._data["trends"].items():
            if len(trend["values"]) >= 10:
                first = statistics.mean(trend["values"][:5])
                last = statistics.mean(trend["values"][-5:])

                if first > 0 and last < first:
                    decline = (first - last) / first
                    problems.append({
                        "metric": key,
                        "decline": round(decline, 3),
                        "current": round(last, 3),
                        "previous": round(first, 3)
                    })

        problems.sort(key=lambda x: x["decline"], reverse=True)
        return problems[:limit]

    def get_metric_history(
        self,
        metric_type: str,
        name: str,
        limit: int = 50
    ) -> List[dict]:
        """Haal history op voor een specifieke metric."""
        key_pattern = f"{metric_type}:{name}"

        history = [
            m for m in self._data["metrics"]
            if f"{m['metric_type']}:{m['name']}" == key_pattern
        ]

        return history[-limit:]

    def set_baseline(self, metric_type: str, name: str, value: float):
        """Stel een baseline in voor een metric."""
        key = f"{metric_type}:{name}"
        self._data["baselines"][key] = {
            "value": value,
            "set_at": datetime.now().isoformat()
        }
        self.save()

    def compare_to_baseline(self, metric_type: str, name: str) -> Optional[dict]:
        """Vergelijk huidige waarde met baseline."""
        key = f"{metric_type}:{name}"

        if key not in self._data["baselines"]:
            return None

        baseline = self._data["baselines"][key]
        trend = self._data["trends"].get(key)

        if not trend or not trend["values"]:
            return None

        current = trend["values"][-1]
        baseline_value = baseline["value"]

        return {
            "baseline": baseline_value,
            "current": current,
            "difference": current - baseline_value,
            "percent_change": (
                (current - baseline_value) / baseline_value * 100
                if baseline_value != 0 else 0
            )
        }

    def record_improvement(
        self,
        description: str,
        metric_key: str,
        before: float,
        after: float
    ):
        """Registreer een significante verbetering."""
        improvement = {
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "metric": metric_key,
            "before": before,
            "after": after,
            "change": after - before,
            "percent_change": (
                (after - before) / before * 100
                if before != 0 else 0
            )
        }
        self._data["improvements"].append(improvement)

        # Keep last 100 improvements
        if len(self._data["improvements"]) > 100:
            self._data["improvements"] = self._data["improvements"][-100:]

        self.save()

    def get_improvements(self, limit: int = 10) -> List[dict]:
        """Haal recente verbeteringen op."""
        return self._data["improvements"][-limit:]


# === CLI voor testing ===

def _cli():
    """Test CLI voor PerformanceAnalyzer."""
    from pathlib import Path

    print("PerformanceAnalyzer Test CLI")
    print("=" * 40)

    pa = PerformanceAnalyzer(Path("data/apps"))

    # Record test metrics
    for i in range(25):
        value = 0.5 + (i * 0.02)  # Gradually improving
        pa.record("test", "example_metric", value)

    print("\nSummary:", pa.get_learning_summary())
    print("\nTrend:", pa.get_trend("test", "example_metric"))


if __name__ == "__main__":
    _cli()
