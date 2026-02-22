import logging
import time

from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

logger = logging.getLogger(__name__)

try:
    from danny_toolkit.core.vector_store import VectorStore
    from danny_toolkit.core.embeddings import get_torch_embedder
    HAS_VECTOR = True
except ImportError:
    HAS_VECTOR = False


class BlackBox:
    """
    INVENTION #13: THE BLACK BOX
    ----------------------------
    Stores 'Anti-Patterns' and 'Lessons Learned'.
    Before answering, the Brain checks this box to see what NOT to do.

    The more failures it records, the fewer hallucinations occur.
    Asymptotically approaches zero repeated mistakes.
    """
    def __init__(self):
        self.db_path = Config.DATA_DIR / "memory" / "black_box.json"
        self._store = None
        self._embedder = None

        if HAS_VECTOR:
            try:
                self._embedder = get_torch_embedder()
                self._store = VectorStore(
                    embedding_provider=self._embedder,
                    db_file=self.db_path,
                )
            except Exception as e:
                logger.debug("VectorStore init failed: %s", e)

    def record_crash(
        self,
        user_prompt: str,
        bad_response: str,
        critique: str,
    ):
        """
        Called when Tribunal rejects an answer.
        Records the failure so it never happens again.
        """
        if not self._store:
            return

        print(f"{Kleur.ROOD}⚫ Black Box: Recording failure...{Kleur.RESET}")

        failure_id = f"failure_{int(time.time())}"
        failure_entry = {
            "id": failure_id,
            "tekst": user_prompt,
            "metadata": {
                "type": "failure_lesson",
                "timestamp": time.time(),
                "hallucination": bad_response[:500],
                "lesson": critique,
            },
        }

        self._store.voeg_toe([failure_entry])
        print(f"{Kleur.GROEN}⚫ Black Box: Lesson recorded.{Kleur.RESET}")

    def retrieve_warnings(
        self,
        current_prompt: str,
        min_score: float = 0.5,
    ) -> str:
        """
        Checks if we are about to make a known mistake.
        Returns a warning string for LLM injection, or empty string.
        """
        if not self._store or not self._store.documenten:
            return ""

        results = self._store.zoek(
            query=current_prompt,
            top_k=1,
            filter_fn=lambda d: d.get("metadata", {}).get("type") == "failure_lesson",
            min_score=min_score,
        )

        if not results:
            return ""

        best = results[0]
        lesson = best.get("metadata", {}).get("lesson", "")
        if not lesson:
            return ""

        print(f"{Kleur.GEEL}⚠️  Black Box Warning: Recalling past "
              f"failure...{Kleur.RESET}")

        return (
            "[SYSTEM WARNING - LEARNED BEHAVIOR]\n"
            f"PAST MISTAKE: When asked about this topic previously, "
            f'you failed by: "{lesson}".\n'
            "CONSTRAINT: Do not repeat this mistake."
        )

    def get_stats(self) -> dict:
        """Return the number of recorded failures."""
        count = len(self._store.documenten) if self._store else 0
        return {"recorded_failures": count}
