"""
Coherentie Monitor — CPU+GPU Load Correlatie Detector
=====================================================

Detecteert onafhankelijke CPU/GPU werking, wat kan wijzen
op ongeautoriseerd GPU-gebruik (bijv. crypto-mining via
gestolen VM).

Detectielogica:
  - GPU hoog (>70%) + CPU laag (<20%) → ALARM
  - Correlatie < -0.1 → ALARM (onafhankelijke werking)
  - Correlatie 0.0–0.3 → WAARSCHUWING
  - Correlatie > 0.3 OF beide idle → PASS

Gebruik:
    from danny_toolkit.daemon.coherentie import (
        CoherentieMonitor,
    )
    monitor = CoherentieMonitor()
    rapport = monitor.scan()
    print(rapport["verdict"])
"""

import logging
import math
import time
import psutil

logger = logging.getLogger(__name__)


class CoherentieMonitor:
    """Meet CPU/GPU correlatie en detecteert anomalieen."""

    def __init__(self):
        self._nvml_beschikbaar = False
        try:
            from pynvml import nvmlInit
            nvmlInit()
            self._nvml_beschikbaar = True
        except Exception as e:
            logger.debug("NVML init failed (no GPU monitoring): %s", e)

    def _meet_cpu(self):
        """Meet huidig CPU-gebruik (percentage)."""
        return psutil.cpu_percent(interval=0)

    def _meet_gpu(self):
        """Meet huidig GPU-gebruik (percentage).

        Returns:
            float: GPU utilization 0-100, of 0.0 als
                   NVML niet beschikbaar is.
        """
        if not self._nvml_beschikbaar:
            return 0.0
        try:
            from pynvml import (
                nvmlDeviceGetHandleByIndex,
                nvmlDeviceGetUtilizationRates,
            )
            handle = nvmlDeviceGetHandleByIndex(0)
            util = nvmlDeviceGetUtilizationRates(handle)
            return float(util.gpu)
        except Exception as e:
            logger.debug("GPU utilization read failed: %s", e)
            return 0.0

    def _bereken_correlatie(self, cpu_reeks, gpu_reeks):
        """Bereken Pearson correlatie tussen twee reeksen.

        Args:
            cpu_reeks: Lijst van CPU percentages.
            gpu_reeks: Lijst van GPU percentages.

        Returns:
            float: Correlatie (-1.0 tot +1.0), of 0.0
                   bij onvoldoende data/variantie.
        """
        n = len(cpu_reeks)
        if n < 2:
            return 0.0

        gem_cpu = sum(cpu_reeks) / n
        gem_gpu = sum(gpu_reeks) / n

        # Covariantie en standaarddeviaties
        cov = sum(
            (c - gem_cpu) * (g - gem_gpu)
            for c, g in zip(cpu_reeks, gpu_reeks)
        ) / n

        std_cpu = math.sqrt(
            sum((c - gem_cpu) ** 2 for c in cpu_reeks) / n
        )
        std_gpu = math.sqrt(
            sum((g - gem_gpu) ** 2 for g in gpu_reeks) / n
        )

        if std_cpu < 0.001 or std_gpu < 0.001:
            return 0.0

        return cov / (std_cpu * std_gpu)

    def _beoordeel(self, cpu_reeks, gpu_reeks, correlatie):
        """Bepaal verdict op basis van metingen.

        Args:
            cpu_reeks: Lijst van CPU percentages.
            gpu_reeks: Lijst van GPU percentages.
            correlatie: Pearson correlatie waarde.

        Returns:
            tuple: (verdict, details) — verdict is
                   "PASS", "WAARSCHUWING" of "ALARM".
        """
        gem_cpu = sum(cpu_reeks) / len(cpu_reeks)
        gem_gpu = sum(gpu_reeks) / len(gpu_reeks)

        # Check 1: Crypto-mining patroon
        if gem_gpu > 70 and gem_cpu < 20:
            return (
                "ALARM",
                f"GPU hoog ({gem_gpu:.1f}%) terwijl "
                f"CPU laag ({gem_cpu:.1f}%) — "
                "mogelijk ongeautoriseerd GPU-gebruik",
            )

        # Check 2: Negatieve correlatie
        if correlatie < -0.1:
            return (
                "ALARM",
                f"Negatieve correlatie ({correlatie:.3f})"
                " — CPU en GPU werken onafhankelijk",
            )

        # Check 3: Lage correlatie
        if 0.0 <= correlatie <= 0.3:
            # Beide idle = normaal
            if gem_cpu < 10 and gem_gpu < 10:
                return (
                    "PASS",
                    f"Beide idle (CPU {gem_cpu:.1f}%,"
                    f" GPU {gem_gpu:.1f}%) — normaal",
                )
            return (
                "WAARSCHUWING",
                f"Lage correlatie ({correlatie:.3f})"
                " — monitor aanbevolen",
            )

        # Check 4: Gezonde correlatie
        return (
            "PASS",
            f"Correlatie {correlatie:.3f} — "
            "CPU en GPU werken coherent",
        )

    def scan(self, samples=20, interval=0.5):
        """Voer een volledige coherentie-scan uit.

        Meet CPU en GPU gebruik over meerdere samples en
        berekent de Pearson correlatie.

        Args:
            samples: Aantal metingen (default 20).
            interval: Seconden tussen metingen (default 0.5).

        Returns:
            dict met:
                cpu_reeks (list[float]),
                gpu_reeks (list[float]),
                cpu_gem (float),
                gpu_gem (float),
                correlatie (float),
                verdict (str),
                details (str),
                gpu_beschikbaar (bool),
                samples (int),
                duur_seconden (float).
        """
        cpu_reeks = []
        gpu_reeks = []

        # Eerste meting om psutil te initialiseren
        psutil.cpu_percent(interval=0)

        start = time.time()
        for _ in range(samples):
            time.sleep(interval)
            cpu_reeks.append(self._meet_cpu())
            gpu_reeks.append(self._meet_gpu())
        duur = time.time() - start

        correlatie = self._bereken_correlatie(
            cpu_reeks, gpu_reeks
        )
        verdict, details = self._beoordeel(
            cpu_reeks, gpu_reeks, correlatie
        )

        gem_cpu = sum(cpu_reeks) / len(cpu_reeks)
        gem_gpu = sum(gpu_reeks) / len(gpu_reeks)

        return {
            "cpu_reeks": cpu_reeks,
            "gpu_reeks": gpu_reeks,
            "cpu_gem": round(gem_cpu, 2),
            "gpu_gem": round(gem_gpu, 2),
            "correlatie": round(correlatie, 4),
            "verdict": verdict,
            "details": details,
            "gpu_beschikbaar": self._nvml_beschikbaar,
            "samples": samples,
            "duur_seconden": round(duur, 2),
        }
