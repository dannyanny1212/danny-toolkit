"""
Groq API Retry — Exponential backoff met SmartKeyManager integratie.

Wrapper voor Groq API calls die:
1. SmartKeyManager.check_throttle() aanroept VOOR de call
2. Exponential backoff uitvoert bij 429
3. SmartKeyManager.registreer_429() aanroept bij rate limit hit
4. Token verbruik registreert na succes

Gebruik:
    from danny_toolkit.core.groq_retry import groq_call_async, groq_call_sync

    response = await groq_call_async(
        client, "AgentName", model="meta-llama/...",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
"""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)

# Defaults
MAX_RETRIES = 3
BASE_DELAY = 2.0  # seconden

try:
    from danny_toolkit.core.key_manager import get_key_manager
    HAS_KEY_MANAGER = True
except ImportError:
    HAS_KEY_MANAGER = False


def _is_rate_limit(error: Exception) -> bool:
    """Detecteer of een exception een 429 rate limit is."""
    err_str = str(error).lower()
    return any(marker in err_str for marker in [
        "429", "rate_limit", "rate limit", "too many requests",
        "resource_exhausted", "quota",
    ])


async def groq_call_async(
    client,
    agent_naam: str,
    model: str,
    messages: list,
    temperature: float = 0.4,
    max_tokens: int = None,
    max_retries: int = MAX_RETRIES,
    **kwargs,
) -> str | None:
    """
    Veilige async Groq API call met throttle check + backoff.

    Returns: response text of None bij falen.
    """
    km = get_key_manager() if HAS_KEY_MANAGER else None

    # Pre-flight throttle check
    if km:
        mag, reden = km.check_throttle(agent_naam, model)
        if not mag:
            logger.info(f"{agent_naam} throttled: {reden}")
            return None

    # API call met exponential backoff
    for poging in range(max_retries):
        try:
            if km:
                km.registreer_request(agent_naam)

            create_kwargs = {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                **kwargs,
            }
            if max_tokens:
                create_kwargs["max_tokens"] = max_tokens

            chat = await client.chat.completions.create(**create_kwargs)
            tekst = chat.choices[0].message.content

            # Registreer verbruik
            if km and tekst:
                km.registreer_tokens(agent_naam, tekst)

            return tekst

        except Exception as e:
            if _is_rate_limit(e):
                if km:
                    km.registreer_429(agent_naam)

                if poging < max_retries - 1:
                    wacht = BASE_DELAY * (2 ** poging)
                    logger.warning(
                        f"{agent_naam}: 429 rate limit — "
                        f"wacht {wacht:.1f}s (poging {poging + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wacht)
                    continue
                else:
                    logger.error(
                        f"{agent_naam}: 429 na {max_retries} pogingen — opgeven"
                    )
                    return None
            else:
                logger.error(f"{agent_naam}: Groq error: {e}")
                return None

    return None


def groq_call_sync(
    client,
    agent_naam: str,
    model: str,
    messages: list,
    temperature: float = 0.4,
    max_tokens: int = None,
    max_retries: int = MAX_RETRIES,
    **kwargs,
) -> str | None:
    """
    Veilige sync Groq API call met throttle check + backoff.

    Gebruikt door CentralBrain (sync pipeline).
    """
    km = get_key_manager() if HAS_KEY_MANAGER else None

    # Pre-flight throttle check
    if km:
        mag, reden = km.check_throttle(agent_naam, model)
        if not mag:
            logger.info(f"{agent_naam} throttled: {reden}")
            return None

    for poging in range(max_retries):
        try:
            if km:
                km.registreer_request(agent_naam)

            create_kwargs = {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                **kwargs,
            }
            if max_tokens:
                create_kwargs["max_tokens"] = max_tokens

            chat = client.chat.completions.create(**create_kwargs)
            tekst = chat.choices[0].message.content

            if km and tekst:
                km.registreer_tokens(agent_naam, tekst)

            return tekst

        except Exception as e:
            if _is_rate_limit(e):
                if km:
                    km.registreer_429(agent_naam)

                if poging < max_retries - 1:
                    wacht = BASE_DELAY * (2 ** poging)
                    logger.warning(
                        f"{agent_naam}: 429 rate limit — "
                        f"wacht {wacht:.1f}s (poging {poging + 1}/{max_retries})"
                    )
                    time.sleep(wacht)
                    continue
                else:
                    logger.error(
                        f"{agent_naam}: 429 na {max_retries} pogingen — opgeven"
                    )
                    return None
            else:
                logger.error(f"{agent_naam}: Groq error: {e}")
                return None

    return None
