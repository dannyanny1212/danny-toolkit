# danny_toolkit/brain/model_sync.py
"""
Multi-Model Sync — Generaal Mode (Phase 41, Invention #25).
============================================================
Externe AI-modellen (GPT, Claude, Gemini, etc.) als huurlingen voor de Swarm.

Trust, but Verify — externe modellen leveren denkkracht, de Swarm levert
wijsheid en veiligheid. Governor + HallucinatieSchild houden de huurlingen
in het gareel.

Betrouwbaarheidsformule:
    R_final = 1 - (1 - P_ext) × (1 - P_shield)

Gebruik:
    from danny_toolkit.brain.model_sync import get_model_registry

    registry = get_model_registry()
    registry.auto_discover()
    workers = registry.get_available()
"""

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from danny_toolkit.core.config import Config

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.key_manager import AgentKeyManager
    HAS_KEY_MANAGER = True
except ImportError:
    HAS_KEY_MANAGER = False


# ── Enums ──

class ModelCapability(str, Enum):
    """Mogelijkheden van een extern model."""
    CODE = "code"
    RESEARCH = "research"
    ANALYSE = "analyse"
    CREATIEF = "creatief"
    VERIFICATIE = "verificatie"


# ── Data Models ──

@dataclass
class ModelProfile:
    """Profiel van een extern AI model."""
    provider: str           # "groq", "anthropic", "openai", "nvidia_nim", "ollama"
    model_id: str           # e.g. Config.LLM_MODEL
    capabilities: List[ModelCapability] = field(default_factory=list)
    cost_tier: int = 1      # 1=gratis, 2=goedkoop, 3=duur
    latency_class: int = 1  # 1=snel, 2=gemiddeld, 3=traag
    max_tokens: int = 4096
    available: bool = True


@dataclass
class ModelResponse:
    """Response van een extern model na generate()."""
    provider: str
    model_id: str
    content: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    passed_barrier: bool = False  # 95% Barrière result
    barrier_score: float = 0.0


@dataclass
class ModelBid:
    """Auction-resultaat: model + score."""
    profile: ModelProfile
    worker: "ModelWorker"
    score: float           # S_model = (cap_match × success_rate) / (cost_tier + latency_class)
    capability_match: float = 0.0


# ── ModelWorker (abstract base) ──

class ModelWorker:
    """
    Basis worker voor een extern AI model.

    Elke worker heeft:
    - Circuit breaker (3 fails → unavailable)
    - Performance tracking (Generaal's geheugen)
    """

    def __init__(self, profile: ModelProfile):
        """**Initializes a new instance with the given profile.

 Args:
     profile (ModelProfile): The profile to use for this instance.

 Attributes:
     profile (ModelProfile): The profile used by this instance.
     _circuit_open (bool): Whether the circuit is currently open.
     _fail_count (int): The current number of failures.
     _max_fails (int): The maximum number of failures allowed.
     _perf (dict): Performance metrics, including calls, successes, failures, barrier rejections, total latency, and total tokens.**"""
        self.profile = profile
        self._circuit_open = False
        self._fail_count = 0
        self._max_fails = 3
        self._perf = {
            "calls": 0,
            "successes": 0,
            "failures": 0,
            "barrier_rejections": 0,
            "total_latency_ms": 0.0,
            "total_tokens": 0,
        }

    async def generate(self, prompt: str, system: str = "") -> ModelResponse:
        """Genereer een response van het model. Override in subclass."""
        raise NotImplementedError

    def is_available(self) -> bool:
        """Controleer of de worker beschikbaar is."""
        return self.profile.available and not self._circuit_open

    def _record_failure(self):
        """Registreer een API fout. 3 fails → circuit open."""
        self._fail_count += 1
        self._perf["failures"] += 1
        if self._fail_count >= self._max_fails:
            self._circuit_open = True
            logger.info("Circuit open voor %s/%s na %d fails",
                        self.profile.provider, self.profile.model_id,
                        self._fail_count)

    def _record_success(self):
        """Registreer een succesvolle call (passed 95% Barrier)."""
        self._fail_count = 0
        self._perf["successes"] += 1

    def _record_barrier_rejection(self):
        """Registreer een 95% Barrière-afwijzing (model ontslagen)."""
        self._perf["barrier_rejections"] += 1

    def success_rate(self) -> float:
        """Historisch percentage dat de 95% Barrière haalt."""
        calls = self._perf["calls"]
        if calls == 0:
            return 0.5  # Default bij 0 calls
        return self._perf["successes"] / calls

    def avg_latency_ms(self) -> float:
        """Gemiddelde latency in milliseconden."""
        calls = self._perf["calls"]
        if calls == 0:
            return 0.0
        return self._perf["total_latency_ms"] / calls

    def get_perf(self) -> dict:
        """Volledige performance snapshot."""
        return {
            **self._perf,
            "success_rate": round(self.success_rate(), 3),
            "avg_latency_ms": round(self.avg_latency_ms(), 1),
            "circuit_open": self._circuit_open,
            "provider": self.profile.provider,
            "model_id": self.profile.model_id,
        }


# ── Provider Workers ──

class GroqModelWorker(ModelWorker):
    """Worker voor Groq API (primaire provider)."""

    def __init__(self, profile: ModelProfile = None):
        if profile is None:
            profile = ModelProfile(
                provider="groq",
                model_id=Config.LLM_MODEL,
                capabilities=[
                    ModelCapability.CODE,
                    ModelCapability.RESEARCH,
                    ModelCapability.ANALYSE,
                    ModelCapability.CREATIEF,
                ],
                cost_tier=1,
                latency_class=1,
                max_tokens=4096,
            )
        super().__init__(profile)
        self._client = None
        try:
            if HAS_KEY_MANAGER:
                self._client = AgentKeyManager.create_async_client("ModelSync")
            if not self._client:
                from groq import AsyncGroq
                self._client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        except ImportError:
            logger.debug("groq SDK niet beschikbaar")
        except Exception as e:
            logger.debug("GroqModelWorker init: %s", e)

    async def generate(self, prompt: str, system: str = "") -> ModelResponse:
        """Genereer via Groq API."""
        self._perf["calls"] += 1
        t0 = time.time()
        try:
            if not self._client:
                raise RuntimeError("Groq client niet beschikbaar")

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = await self._client.chat.completions.create(
                model=self.profile.model_id,
                messages=messages,
                max_tokens=self.profile.max_tokens,
                temperature=0.4,
            )
            content = response.choices[0].message.content or ""
            tokens = getattr(response.usage, "total_tokens", 0)
            latency = (time.time() - t0) * 1000

            self._perf["total_latency_ms"] += latency
            self._perf["total_tokens"] += tokens
            self._fail_count = 0  # Reset on API success

            return ModelResponse(
                provider=self.profile.provider,
                model_id=self.profile.model_id,
                content=content,
                tokens_used=tokens,
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            self._record_failure()
            latency = (time.time() - t0) * 1000
            self._perf["total_latency_ms"] += latency
            logger.debug("GroqModelWorker.generate: %s", e)
            return ModelResponse(
                provider=self.profile.provider,
                model_id=self.profile.model_id,
                content="",
                latency_ms=round(latency, 1),
            )


class AnthropicModelWorker(ModelWorker):
    """Worker voor Anthropic Claude API."""

    def __init__(self, profile: ModelProfile = None):
        if profile is None:
            profile = ModelProfile(
                provider="anthropic",
                model_id=getattr(Config, "CLAUDE_MODEL", "claude-sonnet-4-20250514"),
                capabilities=[
                    ModelCapability.CODE,
                    ModelCapability.RESEARCH,
                    ModelCapability.ANALYSE,
                    ModelCapability.CREATIEF,
                    ModelCapability.VERIFICATIE,
                ],
                cost_tier=3,
                latency_class=2,
                max_tokens=4096,
            )
        super().__init__(profile)
        self._client = None
        try:
            from anthropic import AsyncAnthropic
            key = os.getenv("ANTHROPIC_API_KEY")
            if key:
                self._client = AsyncAnthropic(api_key=key)
        except ImportError:
            logger.debug("anthropic SDK niet beschikbaar")
        except Exception as e:
            logger.debug("AnthropicModelWorker init: %s", e)

    async def generate(self, prompt: str, system: str = "") -> ModelResponse:
        """Genereer via Anthropic API."""
        self._perf["calls"] += 1
        t0 = time.time()
        try:
            if not self._client:
                raise RuntimeError("Anthropic client niet beschikbaar")

            kwargs = {
                "model": self.profile.model_id,
                "max_tokens": self.profile.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system

            response = await self._client.messages.create(**kwargs)
            content = ""
            if response.content:
                content = response.content[0].text
            tokens = getattr(response.usage, "input_tokens", 0) + \
                     getattr(response.usage, "output_tokens", 0)
            latency = (time.time() - t0) * 1000

            self._perf["total_latency_ms"] += latency
            self._perf["total_tokens"] += tokens
            self._fail_count = 0

            return ModelResponse(
                provider=self.profile.provider,
                model_id=self.profile.model_id,
                content=content,
                tokens_used=tokens,
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            self._record_failure()
            latency = (time.time() - t0) * 1000
            self._perf["total_latency_ms"] += latency
            logger.debug("AnthropicModelWorker.generate: %s", e)
            return ModelResponse(
                provider=self.profile.provider,
                model_id=self.profile.model_id,
                content="",
                latency_ms=round(latency, 1),
            )


class OpenAIModelWorker(ModelWorker):
    """Worker voor OpenAI API (GPT-4o-mini, etc.)."""

    def __init__(self, profile: ModelProfile = None):
        if profile is None:
            profile = ModelProfile(
                provider="openai",
                model_id="gpt-4o-mini",
                capabilities=[
                    ModelCapability.CODE,
                    ModelCapability.RESEARCH,
                    ModelCapability.ANALYSE,
                    ModelCapability.CREATIEF,
                ],
                cost_tier=2,
                latency_class=2,
                max_tokens=4096,
            )
        super().__init__(profile)
        self._client = None
        try:
            from openai import AsyncOpenAI
            key = os.getenv("OPENAI_API_KEY")
            if key:
                self._client = AsyncOpenAI(api_key=key)
        except ImportError:
            logger.debug("openai SDK niet beschikbaar")
        except Exception as e:
            logger.debug("OpenAIModelWorker init: %s", e)

    async def generate(self, prompt: str, system: str = "") -> ModelResponse:
        """Genereer via OpenAI API."""
        self._perf["calls"] += 1
        t0 = time.time()
        try:
            if not self._client:
                raise RuntimeError("OpenAI client niet beschikbaar")

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = await self._client.chat.completions.create(
                model=self.profile.model_id,
                messages=messages,
                max_tokens=self.profile.max_tokens,
                temperature=0.4,
            )
            content = response.choices[0].message.content or ""
            tokens = getattr(response.usage, "total_tokens", 0)
            latency = (time.time() - t0) * 1000

            self._perf["total_latency_ms"] += latency
            self._perf["total_tokens"] += tokens
            self._fail_count = 0

            return ModelResponse(
                provider=self.profile.provider,
                model_id=self.profile.model_id,
                content=content,
                tokens_used=tokens,
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            self._record_failure()
            latency = (time.time() - t0) * 1000
            self._perf["total_latency_ms"] += latency
            logger.debug("OpenAIModelWorker.generate: %s", e)
            return ModelResponse(
                provider=self.profile.provider,
                model_id=self.profile.model_id,
                content="",
                latency_ms=round(latency, 1),
            )


class NVIDIAModelWorker(ModelWorker):
    """Worker voor NVIDIA NIM API (OpenAI-compatible)."""

    def __init__(self, profile: ModelProfile = None):
        if profile is None:
            nim_model = getattr(Config, "NVIDIA_NIM_MODEL",
                                "qwen/qwen2.5-coder-32b-instruct")
            profile = ModelProfile(
                provider="nvidia_nim",
                model_id=nim_model,
                capabilities=[
                    ModelCapability.CODE,
                    ModelCapability.ANALYSE,
                ],
                cost_tier=1,
                latency_class=2,
                max_tokens=4096,
            )
        super().__init__(profile)
        self._client = None
        try:
            from openai import AsyncOpenAI
            key = os.getenv("NVIDIA_NIM_API_KEY")
            base_url = os.getenv("NVIDIA_NIM_BASE_URL",
                                 "https://integrate.api.nvidia.com/v1")
            if key:
                self._client = AsyncOpenAI(api_key=key, base_url=base_url)
        except ImportError:
            logger.debug("openai SDK niet beschikbaar (voor NVIDIA NIM)")
        except Exception as e:
            logger.debug("NVIDIAModelWorker init: %s", e)

    async def generate(self, prompt: str, system: str = "") -> ModelResponse:
        """Genereer via NVIDIA NIM API."""
        self._perf["calls"] += 1
        t0 = time.time()
        try:
            if not self._client:
                raise RuntimeError("NVIDIA NIM client niet beschikbaar")

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = await self._client.chat.completions.create(
                model=self.profile.model_id,
                messages=messages,
                max_tokens=self.profile.max_tokens,
                temperature=0.4,
            )
            content = response.choices[0].message.content or ""
            tokens = getattr(response.usage, "total_tokens", 0)
            latency = (time.time() - t0) * 1000

            self._perf["total_latency_ms"] += latency
            self._perf["total_tokens"] += tokens
            self._fail_count = 0

            return ModelResponse(
                provider=self.profile.provider,
                model_id=self.profile.model_id,
                content=content,
                tokens_used=tokens,
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            self._record_failure()
            latency = (time.time() - t0) * 1000
            self._perf["total_latency_ms"] += latency
            logger.debug("NVIDIAModelWorker.generate: %s", e)
            return ModelResponse(
                provider=self.profile.provider,
                model_id=self.profile.model_id,
                content="",
                latency_ms=round(latency, 1),
            )


class GeminiModelWorker(ModelWorker):
    """Worker voor Google Gemini API (google.genai SDK).

    Ondersteunt gemini-2.5-pro, gemini-2.5-flash, etc.
    Key via GOOGLE_API_KEY of GEMINI_API_KEY env var.
    """

    def __init__(self, profile: ModelProfile = None):
        if profile is None:
            gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
            profile = ModelProfile(
                provider="gemini",
                model_id=gemini_model,
                capabilities=[
                    ModelCapability.CODE,
                    ModelCapability.RESEARCH,
                    ModelCapability.ANALYSE,
                    ModelCapability.CREATIEF,
                    ModelCapability.VERIFICATIE,
                ],
                cost_tier=1,
                latency_class=2,
                max_tokens=8192,
            )
        super().__init__(profile)
        self._client = None
        try:
            from google import genai
            key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if key:
                self._client = genai.Client(api_key=key)
        except ImportError:
            logger.debug("google-genai SDK niet beschikbaar")
        except Exception as e:
            logger.debug("GeminiModelWorker init: %s", e)

    async def generate(self, prompt: str, system: str = "") -> ModelResponse:
        """Genereer via Google Gemini API."""
        self._perf["calls"] += 1
        t0 = time.time()
        try:
            if not self._client:
                raise RuntimeError("Gemini client niet beschikbaar")

            import asyncio
            full_prompt = f"{system}\n\n{prompt}" if system else prompt

            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self.profile.model_id,
                contents=full_prompt,
            )
            content = response.text if hasattr(response, "text") else ""
            tokens = 0
            if hasattr(response, "usage_metadata"):
                meta = response.usage_metadata
                tokens = getattr(meta, "total_token_count", 0)
            latency = (time.time() - t0) * 1000

            self._perf["total_latency_ms"] += latency
            self._perf["total_tokens"] += tokens
            self._fail_count = 0

            return ModelResponse(
                provider=self.profile.provider,
                model_id=self.profile.model_id,
                content=content,
                tokens_used=tokens,
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            self._record_failure()
            latency = (time.time() - t0) * 1000
            self._perf["total_latency_ms"] += latency
            logger.debug("GeminiModelWorker.generate: %s", e)
            return ModelResponse(
                provider=self.profile.provider,
                model_id=self.profile.model_id,
                content="",
                latency_ms=round(latency, 1),
            )


class OllamaModelWorker(ModelWorker):
    """Worker voor lokale Ollama modellen."""

    def __init__(self, profile: ModelProfile = None):
        if profile is None:
            profile = ModelProfile(
                provider="ollama",
                model_id=getattr(Config, "VISION_MODEL", "llava:latest"),
                capabilities=[
                    ModelCapability.CODE,
                    ModelCapability.ANALYSE,
                    ModelCapability.CREATIEF,
                ],
                cost_tier=1,
                latency_class=3,
                max_tokens=4096,
            )
        super().__init__(profile)
        self._client = None
        try:
            from ollama import AsyncClient
            self._client = AsyncClient()
        except ImportError:
            logger.debug("ollama SDK niet beschikbaar")
        except Exception as e:
            logger.debug("OllamaModelWorker init: %s", e)

    async def generate(self, prompt: str, system: str = "") -> ModelResponse:
        """Genereer via Ollama lokaal."""
        self._perf["calls"] += 1
        t0 = time.time()
        try:
            if not self._client:
                raise RuntimeError("Ollama client niet beschikbaar")

            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            response = await self._client.generate(
                model=self.profile.model_id,
                prompt=full_prompt,
            )
            content = response.get("response", "") if isinstance(response, dict) else str(response)
            latency = (time.time() - t0) * 1000

            self._perf["total_latency_ms"] += latency
            self._fail_count = 0

            return ModelResponse(
                provider=self.profile.provider,
                model_id=self.profile.model_id,
                content=content,
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            self._record_failure()
            latency = (time.time() - t0) * 1000
            self._perf["total_latency_ms"] += latency
            logger.debug("OllamaModelWorker.generate: %s", e)
            return ModelResponse(
                provider=self.profile.provider,
                model_id=self.profile.model_id,
                content="",
                latency_ms=round(latency, 1),
            )


# ── ModelRegistry ──

class ModelRegistry:
    """
    Registry van beschikbare externe AI-modellen.

    Auto-discover: checkt env vars en registreert beschikbare workers.
    Thread-safe via Lock.
    """

    def __init__(self):
        self._workers: Dict[str, ModelWorker] = {}
        self._lock = threading.Lock()

    def auto_discover(self):
        """Check env vars en registreer beschikbare workers automatisch."""
        # Groq — primary (llama-4-scout)
        if os.getenv("GROQ_API_KEY"):
            try:
                self.register(GroqModelWorker())
            except Exception as e:
                logger.debug("Groq primary auto-discover: %s", e)

            # Groq — fallback (qwen3-32b)
            try:
                fallback_model = getattr(Config, "LLM_FALLBACK_MODEL", "qwen/qwen3-32b")
                fallback_profile = ModelProfile(
                    provider="groq",
                    model_id=fallback_model,
                    capabilities=[
                        ModelCapability.CODE,
                        ModelCapability.RESEARCH,
                        ModelCapability.ANALYSE,
                        ModelCapability.CREATIEF,
                    ],
                    cost_tier=1,
                    latency_class=1,
                    max_tokens=4096,
                )
                self.register(GroqModelWorker(profile=fallback_profile))
            except Exception as e:
                logger.debug("Groq fallback auto-discover: %s", e)

        # Anthropic — gated by ALLOW_ANTHROPIC
        if Config.ALLOW_ANTHROPIC and os.getenv("ANTHROPIC_API_KEY"):
            try:
                self.register(AnthropicModelWorker())
            except Exception as e:
                logger.debug("Anthropic auto-discover: %s", e)

        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                self.register(OpenAIModelWorker())
            except Exception as e:
                logger.debug("OpenAI auto-discover: %s", e)

        # NVIDIA NIM
        if os.getenv("NVIDIA_NIM_API_KEY"):
            try:
                self.register(NVIDIAModelWorker())
            except Exception as e:
                logger.debug("NVIDIA NIM auto-discover: %s", e)

        # Google Gemini
        if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
            try:
                self.register(GeminiModelWorker())
            except Exception as e:
                logger.debug("Gemini auto-discover: %s", e)

        # Ollama — try to connect
        try:
            import ollama
            self.register(OllamaModelWorker())
        except ImportError:
            logger.debug("Ollama SDK not available, skipping worker")
        except Exception as e:
            logger.debug("Ollama auto-discover: %s", e)

        logger.info("ModelRegistry: %d workers ontdekt", len(self._workers))

    def register(self, worker: ModelWorker):
        """Registreer een worker handmatig."""
        key = f"{worker.profile.provider}/{worker.profile.model_id}"
        with self._lock:
            self._workers[key] = worker
        logger.debug("ModelRegistry: geregistreerd %s", key)

    def get_available(self) -> List[ModelWorker]:
        """Geef alle beschikbare (niet-circuit-open) workers."""
        with self._lock:
            return [w for w in self._workers.values() if w.is_available()]

    def get_by_provider(self, provider: str) -> Optional[ModelWorker]:
        """Zoek eerste beschikbare worker voor een provider."""
        with self._lock:
            for w in self._workers.values():
                if w.profile.provider == provider and w.is_available():
                    return w
        return None

    def get_all_workers(self) -> List[ModelWorker]:
        """Geef alle workers (ook circuit-open)."""
        with self._lock:
            return list(self._workers.values())

    def get_stats(self) -> dict:
        """Registry statistieken voor Observatory."""
        with self._lock:
            workers = list(self._workers.values())
        return {
            "total_workers": len(workers),
            "available_workers": sum(1 for w in workers if w.is_available()),
            "workers": [w.get_perf() for w in workers],
        }


# ── Singleton Factory ──

_registry_instance: Optional[ModelRegistry] = None
_registry_lock = threading.Lock()


def get_model_registry() -> ModelRegistry:
    """Return the process-wide ModelRegistry singleton (double-checked locking)."""
    global _registry_instance
    if _registry_instance is None:
        with _registry_lock:
            if _registry_instance is None:
                _registry_instance = ModelRegistry()
    return _registry_instance


# ── Betrouwbaarheidsformule ──

def betrouwbaarheid(p_ext: float, p_shield: float) -> float:
    """
    R_final = 1 - (1 - P_ext) × (1 - P_shield)

    Args:
        p_ext: Kans dat het externe model correct is (0.0 - 1.0)
        p_shield: Detectiekans interne audit (0.0 - 1.0)

    Returns:
        Totale betrouwbaarheid (0.0 - 1.0)
    """
    return 1.0 - (1.0 - p_ext) * (1.0 - p_shield)
