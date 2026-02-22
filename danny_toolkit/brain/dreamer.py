import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

from groq import AsyncGroq
from danny_toolkit.core.config import Config
from danny_toolkit.core.utils import Kleur

try:
    from danny_toolkit.core.key_manager import get_key_manager
    HAS_KEY_MANAGER = True
except ImportError:
    HAS_KEY_MANAGER = False

try:
    from danny_toolkit.brain.cortical_stack import get_cortical_stack
    HAS_STACK = True
except ImportError:
    HAS_STACK = False

try:
    from danny_toolkit.brain.the_mirror import TheMirror
    HAS_MIRROR = True
except ImportError:
    HAS_MIRROR = False


class Dreamer:
    """
    THE DREAMER (Invention #10)
    ---------------------------
    Runs maintenance while you sleep.

    1. Vacuum: Optimize SQLite CorticalStack
    2. Compress: Summarize last 24h into a daily digest
    3. Reflect: Update user profile via TheMirror
    4. Pre-Compute: Anticipate tomorrow's needs
    """
    def __init__(self):
        if HAS_KEY_MANAGER:
            km = get_key_manager()
            self.client = km.create_async_client("Dreamer") or AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        else:
            self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = Config.LLM_MODEL

    async def rem_cycle(self):
        """Full REM cycle — run at 04:00 via daemon_heartbeat."""
        print(f"{Kleur.MAGENTA}🌙 Entering REM cycle (System Optimization)...{Kleur.RESET}")

        # 0. Backup — before any destructive operations
        self._backup_cortical_stack()

        # 1. Vacuum — optimize SQLite
        self._vacuum()

        # 1.5. Retention — prune old rows, then vacuum reclaims space
        self._apply_retention()

        # 2. Compress — daily summary
        await self._compress()

        # 3. Reflect — update user profile
        if HAS_MIRROR:
            mirror = TheMirror()
            await mirror.reflect()

        # 4. Self-document — GhostWriter haunt
        try:
            from danny_toolkit.brain.ghost_writer import GhostWriter
            writer = GhostWriter()
            await writer.haunt()
        except Exception as e:
            logger.debug("GhostWriter haunt error: %s", e)

        # 5. Research failures — fill knowledge gaps overnight
        await self._research_failures()

        # 5.5 Synapse pruning — decay unused pathways
        try:
            from danny_toolkit.brain.synapse import TheSynapse
            synapse = TheSynapse()
            synapse.decay_unused(days_threshold=7)
            print(f"{Kleur.GROEN}🧠 Synapse pruning complete.{Kleur.RESET}")
        except Exception as e:
            logger.debug("Synapse pruning error: %s", e)

        # 5.6 Phantom rebuild — temporal pattern analysis
        try:
            from danny_toolkit.brain.phantom import ThePhantom
            phantom = ThePhantom()
            phantom.update_patterns()
            print(f"{Kleur.GROEN}👻 Phantom patterns rebuilt.{Kleur.RESET}")
        except Exception as e:
            logger.debug("Phantom rebuild error: %s", e)

        # 6. Pre-Compute — anticipate tomorrow
        insight = await self._anticipate()
        if insight:
            print(f"{Kleur.CYAAN}✨ Morning Insight: {insight}{Kleur.RESET}")

        # 7. Oracle Eye — dagelijkse resource forecast
        try:
            from danny_toolkit.brain.oracle_eye import TheOracleEye
            oracle = TheOracleEye()
            forecast = oracle.generate_daily_forecast()
            if forecast:
                print(f"{Kleur.CYAAN}🔮 {forecast.split(chr(10))[0]}{Kleur.RESET}")
        except Exception as e:
            logger.debug("OracleEye forecast error: %s", e)

        print(f"{Kleur.GROEN}🌙 REM cycle complete.{Kleur.RESET}")

    def _backup_cortical_stack(self):
        """Create a compressed backup of cortical_stack.db."""
        if not HAS_STACK:
            return
        print(f"{Kleur.GEEL}💾 Backing up CorticalStack...{Kleur.RESET}")
        try:
            stack = get_cortical_stack()
            backup_path = stack.backup(compress=True)
            print(f"{Kleur.GROEN}💾 Backup created: {backup_path.name}{Kleur.RESET}")
        except Exception as e:
            print(f"{Kleur.ROOD}💾 Backup error: {e}{Kleur.RESET}")

    def _apply_retention(self):
        """Apply data retention policy to prune old rows."""
        if not HAS_STACK:
            return
        print(f"{Kleur.GEEL}🗑️ Applying retention policy...{Kleur.RESET}")
        try:
            stack = get_cortical_stack()
            deleted = stack.apply_retention_policy()
            total = sum(deleted.values())
            if total > 0:
                details = ", ".join(f"{t}: {c}" for t, c in deleted.items() if c > 0)
                print(f"{Kleur.GROEN}🗑️ Retention: {total} rows pruned ({details}){Kleur.RESET}")
            else:
                print(f"{Kleur.GROEN}🗑️ Retention: no old data to prune.{Kleur.RESET}")
        except Exception as e:
            print(f"{Kleur.ROOD}🗑️ Retention error: {e}{Kleur.RESET}")

    def _vacuum(self):
        """Optimize the CorticalStack SQLite database."""
        if not HAS_STACK:
            return
        print(f"{Kleur.GEEL}🧹 Vacuuming CorticalStack...{Kleur.RESET}")
        stack = get_cortical_stack()
        stack.flush()
        try:
            stack._conn.execute("VACUUM")
            print(f"{Kleur.GROEN}🧹 Vacuum complete.{Kleur.RESET}")
        except Exception as e:
            print(f"{Kleur.ROOD}🧹 Vacuum error: {e}{Kleur.RESET}")

    async def _compress(self):
        """Summarize last 24h of events into a daily digest."""
        if not HAS_STACK:
            return
        print(f"{Kleur.GEEL}📝 Compressing daily log...{Kleur.RESET}")
        stack = get_cortical_stack()
        events = stack.get_recent_events(count=100)

        if not events:
            return

        # Filter to last 24h
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        recent = [e for e in events if e.get("timestamp", "") >= cutoff]

        if not recent:
            return

        try:
            prompt = (
                "Summarize these system events from the last 24 hours into "
                "a concise daily digest (max 5 bullet points, Dutch):\n\n"
                f"{json.dumps(recent, default=str, ensure_ascii=False)}"
            )
            chat = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.3,
            )
            summary = chat.choices[0].message.content

            # Store digest back into CorticalStack
            stack.log_event(
                actor="dreamer",
                action="daily_digest",
                details={"summary": summary, "event_count": len(recent)},
                source="dreamer",
            )
            stack.flush()
            print(f"{Kleur.GROEN}📝 Daily digest stored ({len(recent)} events).{Kleur.RESET}")
        except Exception as e:
            print(f"{Kleur.ROOD}📝 Compress error: {e}{Kleur.RESET}")

    async def _anticipate(self) -> Optional[str]:
        """Analyze today's work to predict tomorrow's needs."""
        if not HAS_STACK:
            return None
        print(f"{Kleur.GEEL}🔮 Anticipating tomorrow...{Kleur.RESET}")
        stack = get_cortical_stack()
        events = stack.get_recent_events(count=50)

        if not events:
            return None

        try:
            prompt = (
                "Based on these recent user activities, predict what the user "
                "will likely work on tomorrow. Be specific about files and "
                "modules. One sentence, Dutch.\n\n"
                f"{json.dumps(events, default=str, ensure_ascii=False)}"
            )
            chat = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.5,
            )
            return chat.choices[0].message.content
        except Exception as e:
            print(f"{Kleur.ROOD}🔮 Anticipation error: {e}{Kleur.RESET}")
            return None

    async def _research_failures(self):
        """Research top failure topics via VoidWalker."""
        try:
            from danny_toolkit.brain.black_box import BlackBox
            from danny_toolkit.brain.void_walker import VoidWalker
            bb = BlackBox()
            stats = bb.get_stats()
            if stats.get("recorded_failures", 0) == 0:
                return
            print(f"{Kleur.GEEL}🔬 Researching past failures...{Kleur.RESET}")
            walker = VoidWalker()
            if bb._store and bb._store.documenten:
                topics = set()
                for doc_id, doc in (
                    bb._store.documenten.items()
                    if isinstance(bb._store.documenten, dict)
                    else enumerate(bb._store.documenten)
                ):
                    tekst = doc.get("tekst", "") if isinstance(doc, dict) else ""
                    if tekst:
                        topics.add(tekst[:100])
                for topic in list(topics)[:3]:
                    await walker.fill_knowledge_gap(topic)
            print(f"{Kleur.GROEN}🔬 Failure research complete.{Kleur.RESET}")
        except Exception as e:
            logger.debug("Failure research error: %s", e)
