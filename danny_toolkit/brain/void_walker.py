import json
import os
import time
from typing import List, Optional, Tuple

from groq import AsyncGroq
from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

try:
    from danny_toolkit.core.web_scraper import scrape_url
    HAS_SCRAPER = True
except ImportError:
    HAS_SCRAPER = False

try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        HAS_DDGS = True
    except ImportError:
        HAS_DDGS = False

try:
    from danny_toolkit.core.vector_store import VectorStore
    from danny_toolkit.core.embeddings import get_torch_embedder
    HAS_VECTOR = True
except ImportError:
    HAS_VECTOR = False


# Domains die meer ruis dan kennis opleveren
_BLACKLIST = [
    "pinterest.com", "youtube.com", "reddit.com",
    "facebook.com", "instagram.com", "tiktok.com",
]


class VoidWalker:
    """
    INVENTION #14: THE VOID WALKER
    ------------------------------
    An autonomous agent that hunts for knowledge to fill gaps.
    It turns 'Unknowns' into 'Embeddings'.

    Flow:
        1. Scout  — search DuckDuckGo for documentation
        2. Harvest — scrape top 3 high-quality pages
        3. Digest  — summarize via Groq 70B
        4. Integrate — ingest into VectorStore
    """
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "mixtral-8x7b-32768"
        self.db_path = Config.DATA_DIR / "memory" / "knowledge_companion.json"

        self._store = None
        if HAS_VECTOR:
            try:
                embedder = get_torch_embedder()
                self._store = VectorStore(
                    embedding_provider=embedder,
                    db_file=self.db_path,
                )
            except Exception:
                pass

    async def fill_knowledge_gap(self, topic: str) -> Optional[str]:
        """
        Full research cycle: scout → harvest → digest → integrate.
        """
        print(f"{Kleur.MAGENTA}🌌 Void Walker: Entering the void "
              f"for '{topic}'...{Kleur.RESET}")

        # 1. SCOUT
        if not HAS_DDGS:
            print(f"{Kleur.ROOD}🌌 Void Walker: duckduckgo-search "
                  f"niet geinstalleerd.{Kleur.RESET}")
            return None

        links = self._search(topic)
        if not links:
            print(f"{Kleur.ROOD}🌌 Void Walker: Geen bronnen "
                  f"gevonden.{Kleur.RESET}")
            return None

        # 2. HARVEST
        knowledge_buffer = ""
        for title, url in links[:3]:
            print(f"  > Extracting: {title}")
            content = self._harvest(url)
            if content:
                knowledge_buffer += (
                    f"SOURCE: {title} ({url})\n"
                    f"CONTENT: {content[:2000]}\n\n"
                )

        if not knowledge_buffer:
            return None

        # 3. DIGEST
        print(f"{Kleur.MAGENTA}🧠 Void Walker: Digesting data...{Kleur.RESET}")
        clean_knowledge = await self._digest(topic, knowledge_buffer)

        if not clean_knowledge:
            return None

        # 4. INTEGRATE
        if self._store:
            entry_id = f"voidwalker_{int(time.time())}"
            self._store.voeg_toe([{
                "id": entry_id,
                "tekst": clean_knowledge,
                "metadata": {
                    "source": "void_walker",
                    "topic": topic,
                    "timestamp": time.time(),
                },
            }])
            print(f"{Kleur.GROEN}✨ Void Walker: Knowledge acquired. "
                  f"'{topic}' is now known.{Kleur.RESET}")
        else:
            print(f"{Kleur.GEEL}🌌 Void Walker: Geen VectorStore — "
                  f"kennis niet opgeslagen.{Kleur.RESET}")

        return clean_knowledge

    def _search(self, query: str) -> List[Tuple[str, str]]:
        """Search DuckDuckGo for documentation pages."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            clean = []
            for r in results:
                href = r.get("href", "")
                if not any(b in href for b in _BLACKLIST):
                    clean.append((r.get("title", ""), href))
            return clean
        except Exception as e:
            print(f"{Kleur.ROOD}🌌 Search failed: {e}{Kleur.RESET}")
            return []

    def _harvest(self, url: str) -> Optional[str]:
        """Scrape a URL using the existing web_scraper module."""
        if not HAS_SCRAPER:
            return None
        try:
            chunks = scrape_url(url, chunk_size=2000, overlap=0)
            if chunks:
                return " ".join(c["text"] for c in chunks[:3])
            return None
        except Exception:
            return None

    async def _digest(self, topic: str, raw_text: str) -> Optional[str]:
        """Summarize raw scraped text into clean knowledge via Groq."""
        prompt = (
            f"Synthesize the following raw text into a technical "
            f"knowledge entry about '{topic}'.\n"
            f"Focus on facts, syntax, and definitions. "
            f"Ignore ads and fluff.\n\n"
            f"RAW TEXT:\n{raw_text}"
        )
        try:
            chat = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.3,
            )
            return chat.choices[0].message.content
        except Exception as e:
            print(f"{Kleur.ROOD}🌌 Digest error: {e}{Kleur.RESET}")
            return None
