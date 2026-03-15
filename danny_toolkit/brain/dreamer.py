"""
Dreamer — Overnight REM Cycle (v6.0 Invention).



Draait om 04:00 via daemon heartbeat. Voert uit: CorticalStack backup,
vacuum, retention policy, GhostWriter auto-docstrings, TheMirror
user profiling, Phantom anticipation, en Synapse pathway plasticity.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from groq import AsyncGroq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

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

try:
    from danny_toolkit.core.alerter import get_alerter, AlertLevel
    HAS_ALERTER = True
except ImportError:
    HAS_ALERTER = False


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
    def __init__(self) -> None:
        """Initializes the instance with a Groq API client and model configuration.

If the key manager is available, creates an asynchronous Groq client using the key manager; 
otherwise, falls back to using the GROQ_API_KEY environment variable.

Sets the model attribute to the LLM model specified in the configuration."""
        if not HAS_GROQ:
            self.client = None
        elif HAS_KEY_MANAGER:
            km = get_key_manager()
            self.client = km.create_async_client("Dreamer")
            if not self.client:
                self.client = AsyncGroq(api_key=km.get_key("Dreamer"))
        else:
            self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = Config.LLM_MODEL

    async def rem_cycle(self) -> None:
        """Full REM cycle — run at 04:00 via daemon_heartbeat."""
        logger.info("🌙 Entering REM cycle (System Optimization)...")

        # 0. Backup — before any destructive operations
        self._backup_cortical_stack()

        # 1. Vacuum — optimize SQLite
        self._vacuum()

        # 1.5. Retention — prune old rows, then vacuum reclaims space
        self._apply_retention()

        # 1.6. Log rotation — verwijder oude log bestanden
        self._rotate_logs()

        # 2. Compress — daily summary
        await self._compress()

        # 3. Reflect — update user profile
        if HAS_MIRROR:
            mirror = TheMirror()
            await mirror.reflect()

        # 4. Self-document — GhostWriter haunt (Phase 38: write-back)
        try:
            from danny_toolkit.brain.ghost_writer import GhostWriter
            writer = GhostWriter()
            _gw_dry_run = getattr(Config, "GHOSTWRITER_DRY_RUN", True)
            _gw_max = getattr(Config, "GHOSTWRITER_MAX_PER_CYCLE", 10)
            await writer.haunt(dry_run=_gw_dry_run, max_functies=_gw_max)
        except Exception as e:
            logger.debug("GhostWriter haunt error: %s", e)

        # 5. Research failures — fill knowledge gaps overnight
        await self._research_failures()

        # 5.5 Synapse pruning — decay unused pathways
        try:
            from danny_toolkit.brain.synapse import get_synapse
            synapse = get_synapse()
            synapse.decay_unused(days_threshold=7)
            pruned = synapse.prune_dead_pathways(min_fires=5)
            logger.info("🧠 Synapse pruning complete (%d dead removed).", pruned)
        except Exception as e:
            logger.debug("Synapse pruning error: %s", e)

        # 5.6 Phantom rebuild — temporal pattern analysis
        try:
            from danny_toolkit.brain.phantom import get_phantom
            phantom = get_phantom()
            phantom.update_patterns()
            print(f"{Kleur.GROEN}👻 Phantom patterns rebuilt.{Kleur.RESET}")
        except Exception as e:
            logger.debug("Phantom rebuild error: %s", e)

        # 5.7 Shadow Summarization — pre-summarize RAG documents
        await self._shadow_summarization()

        # 5.8 Recursive Refiner — dubbele pers naar Super-Tokens
        await self._recursive_refine()

        # 5.9 Semantic Cache eviction — verwijder verlopen entries
        try:
            from danny_toolkit.core.semantic_cache import get_semantic_cache
            sc = get_semantic_cache()
            sc.evict_expired()
            sc_stats = sc.stats()
            logger.info("SemanticCache maintenance: %d entries, %d hits",
                        sc_stats.get("total_entries", 0),
                        sc_stats.get("total_hits", 0))
        except Exception as e:
            logger.debug("SemanticCache REM maintenance failed: %s", e)

        # 5.10 ConfigAuditor REM check — drift detectie
        try:
            from danny_toolkit.brain.config_auditor import get_config_auditor
            auditor = get_config_auditor()
            audit_rapport = auditor.audit()
            if audit_rapport.drift_gedetecteerd:
                print(f"{Kleur.GEEL}🔍 Config drift gedetecteerd: "
                      f"{len([s for s in audit_rapport.schendingen if s.categorie == 'drift'])} "
                      f"wijzigingen{Kleur.RESET}")
            elif not audit_rapport.veilig:
                print(f"{Kleur.ROOD}🔍 Config audit: "
                      f"{len(audit_rapport.schendingen)} schendingen{Kleur.RESET}")
            else:
                print(f"{Kleur.GROEN}🔍 Config audit: veilig{Kleur.RESET}")
        except Exception as e:
            logger.debug("ConfigAuditor REM check failed: %s", e)

        # 5.11 ShardRouter auto-migratie check
        try:
            from danny_toolkit.core.config import Config as _Cfg
            if getattr(_Cfg, "SHARD_ENABLED", False):
                from danny_toolkit.core.shard_router import get_shard_router
                router = get_shard_router()
                stats = router.statistieken()
                totaal_shards = sum(s.aantal_chunks for s in stats)
                if totaal_shards == 0:
                    print(f"{Kleur.GEEL}🔀 Shard migratie gestart...{Kleur.RESET}")
                    resultaat = router.migreer()
                    gemigreerd = sum(resultaat.values())
                    print(f"{Kleur.GROEN}🔀 Shard migratie: {gemigreerd} chunks verdeeld{Kleur.RESET}")
                else:
                    print(f"{Kleur.GROEN}🔀 Shards actief: {totaal_shards} chunks{Kleur.RESET}")
        except Exception as e:
            logger.debug("ShardRouter REM migratie check failed: %s", e)

        # 5.12 SelfPruning — vector store onderhoud
        try:
            from danny_toolkit.core.self_pruning import get_self_pruning
            sp = get_self_pruning()
            prune_result = sp.prune()
            if prune_result.get("overgeslagen"):
                print(f"{Kleur.GEEL}🗑️ SelfPruning: uitgeschakeld (PRUNING_ENABLED=False){Kleur.RESET}")
            else:
                ga = prune_result.get("gearchiveerd", 0)
                vn = prune_result.get("vernietigd", 0)
                ef = prune_result.get("entropie_geflagd", 0)
                ms = prune_result.get("duur_ms", 0)
                print(f"{Kleur.GROEN}🗑️ SelfPruning: {ga} gearchiveerd, "
                      f"{vn} vernietigd, {ef} entropie-flagged ({ms}ms){Kleur.RESET}")
        except Exception as e:
            logger.debug("SelfPruning REM cycle failed: %s", e)

        # 5.13 Cortex maintenance — prune lage confidence, merge duplicaten
        try:
            from danny_toolkit.brain.cortex import TheCortex
            cortex = TheCortex()
            _cx_stats_before = cortex.get_stats()
            _cx_gepruned = 0
            _cx_gemerged = 0

            # Prune triples met confidence < 0.2
            if hasattr(cortex, "_stack") and cortex._stack:
                try:
                    with cortex._stack._lock:
                        cursor = cortex._stack._conn.execute(
                            "DELETE FROM knowledge_graph WHERE confidence < 0.2"
                        )
                        _cx_gepruned = cursor.rowcount
                        cortex._stack._conn.commit()
                except Exception as e:
                    logger.debug("Cortex triple prune fout: %s", e)

            # Rebuild in-memory graph als er wijzigingen zijn
            if _cx_gepruned > 0 and hasattr(cortex, "_build_graph"):
                cortex._build_graph()

            _cx_stats_after = cortex.get_stats()

            if HAS_STACK:
                try:
                    stack = get_cortical_stack()
                    stack.log_event(
                        actor="dreamer",
                        action="cortex_maintenance",
                        details={
                            "gepruned_triples": _cx_gepruned,
                            "gemerged_entities": _cx_gemerged,
                            "nodes_before": _cx_stats_before.get("graph_nodes", 0),
                            "nodes_after": _cx_stats_after.get("graph_nodes", 0),
                        },
                    )
                except Exception as e:
                    logger.debug("CorticalStack cortex log fout: %s", e)

            print(f"{Kleur.GROEN}Knowledge Graph maintenance: "
                  f"{_cx_gepruned} triples gepruned{Kleur.RESET}")
        except Exception as e:
            logger.debug("Cortex REM maintenance error: %s", e)

        # 5.14 Phantom pre-warm — pre-warm MEMEX context voor morgen
        try:
            from danny_toolkit.brain.phantom import get_phantom
            phantom = get_phantom()
            phantom.pre_warm_context()
            pre_warmed_count = len(phantom._pre_warmed)
            print(f"{Kleur.GROEN}👻 Phantom pre-warm: {pre_warmed_count} categorieën geladen{Kleur.RESET}")
        except Exception as e:
            logger.debug("Phantom pre-warm REM failed: %s", e)

        # 6. Pre-Compute — anticipate tomorrow
        insight = await self._anticipate()
        if insight:
            print(f"{Kleur.CYAAN}✨ Morning Insight: {insight}{Kleur.RESET}")

        # 6.5 Learning System — run self-improvement cycle
        try:
            from danny_toolkit.learning import LearningSystem
            ls = LearningSystem()
            cycle_result = ls.run_learning_cycle()
            improvements = cycle_result.get("learning_cycle", {})
            adapted = improvements.get("adaptations_applied", 0) if isinstance(improvements, dict) else 0
            print(f"{Kleur.GROEN}🧠 Learning cycle: {adapted} adaptations applied{Kleur.RESET}")
        except Exception as e:
            logger.debug("Learning cycle REM failed: %s", e)

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

    def _backup_cortical_stack(self) -> None:
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
            if HAS_ALERTER:
                try:
                    get_alerter().alert(
                        AlertLevel.KRITIEK,
                        f"CorticalStack backup mislukt: {e}",
                        bron="dreamer",
                    )
                except Exception as e:
                    logger.debug("REM taak mislukt: %s", e)

    def _apply_retention(self) -> None:
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

    def _rotate_logs(self) -> None:
        """Verwijder oude log bestanden uit data/logs/."""
        try:
            from danny_toolkit.core.log_rotation import roteer_logs
            verwijderd = roteer_logs(Config.DATA_DIR / "logs", max_leeftijd_dagen=30)
            if verwijderd > 0:
                print(f"{Kleur.GROEN}🗂️ Log rotation: {verwijderd} bestand(en) verwijderd.{Kleur.RESET}")
        except Exception as e:
            logger.debug("Log rotation error: %s", e)

    def _vacuum(self) -> None:
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

    async def _compress(self) -> None:
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
            summary = chat.choices[0].message.content if chat.choices else ""

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
            return chat.choices[0].message.content if chat.choices else ""
        except Exception as e:
            print(f"{Kleur.ROOD}🔮 Anticipation error: {e}{Kleur.RESET}")
            return None

    async def _shadow_summarization(self, max_docs: int = 10) -> None:
        """REM Fase 5.7: Shadow pre-summarization of RAG documents.

        Gebruikt de Dreamer's eigen Groq client (GROQ_API_KEY_OVERNIGHT)
        i.p.v. ShadowKeyVault, zodat batch summarization niet geblokkeerd
        wordt door de shadow throttle.

        Args:
            max_docs: Max documenten per cyclus (standaard 10).
        """
        print(f"{Kleur.GEEL}📑 Shadow summarization starting...{Kleur.RESET}")
        try:
            from danny_toolkit.brain.virtual_twin import ShadowCortex
        except ImportError:
            logger.debug("ShadowCortex not available")
            return

        # ChromaDB toegang
        try:
            import chromadb
            db_pad = str(Config.RAG_DATA_DIR / "chromadb")
            chroma_client = chromadb.PersistentClient(path=db_pad)
            collections = chroma_client.list_collections()
            if not collections:
                logger.debug("Shadow summarization: geen ChromaDB collections")
                return
        except Exception as e:
            logger.debug("Shadow summarization: ChromaDB mislukt: %s", e)
            return

        try:
            sc = ShadowCortex()

            # Verzamel alle chunks uit alle collections
            alle_ids = []
            alle_texts = []
            for col in collections:
                collection = chroma_client.get_collection(col.name)
                count = collection.count()
                if count == 0:
                    continue
                peek = collection.peek(limit=min(50, count))
                alle_ids.extend(peek.get("ids", []))
                alle_texts.extend(peek.get("documents", []))

            # Filter kandidaten: niet te kort, niet al samengevat
            # Haal alle bestaande hashes in één query (batch i.p.v. N+1)
            filter_conn = sc._get_summary_conn()
            bestaande_hashes = {}
            try:
                if alle_ids:
                    placeholders = ",".join("?" for _ in alle_ids)
                    rows = filter_conn.execute(
                        f"SELECT doc_id, doc_hash FROM shadow_summaries WHERE doc_id IN ({placeholders})",
                        alle_ids,
                    ).fetchall()
                    bestaande_hashes = {r[0]: r[1] for r in rows}
            except Exception as e:
                logger.debug("Batch hash lookup failed: %s", e)

            candidates = []
            gezien_ids = set()
            for doc_id, tekst in zip(alle_ids, alle_texts):
                if not tekst or len(tekst) < 200:
                    continue
                if doc_id in gezien_ids:
                    continue
                gezien_ids.add(doc_id)
                doc_hash = sc._doc_hash(tekst)
                if bestaande_hashes.get(doc_id) == doc_hash:
                    continue
                candidates.append((doc_id, tekst, len(tekst)))

            if not candidates:
                print(f"{Kleur.GROEN}📑 Shadow summarization: alle documenten up to date.{Kleur.RESET}")
                return

            print(f"{Kleur.CYAAN}📑 {len(candidates)} kandidaten gevonden, verwerken...{Kleur.RESET}")

            # Sorteer op grootte (grootste besparing eerst)
            candidates.sort(key=lambda x: x[2], reverse=True)

            # Verwerk met Dreamer's eigen client (geen ShadowKeyVault throttle)
            samengevat = 0
            totaal_bespaard = 0

            # Deduplicatie op doc_id
            gezien = set()
            unieke_candidates = []
            for c in candidates[:max_docs]:
                if c[0] not in gezien:
                    gezien.add(c[0])
                    unieke_candidates.append(c)

            conn = sc._get_summary_conn()
            try:
                for doc_id, tekst, length in unieke_candidates:
                    prompt = (
                        "Comprimeer de volgende tekst tot maximaal 30% van het origineel.\n"
                        "REGELS:\n"
                        "- Maximaal 2 zinnen.\n"
                        "- Bewaar ALLEEN: feiten, namen, cijfers, technische termen.\n"
                        "- Verwijder: meningen, voorbeelden, herhaling, opvulwoorden, inleidingen.\n"
                        "- Gebruik telegramstijl: kort, direct, geen bijzinnen.\n"
                        "- Antwoord ALLEEN met de compressie, geen uitleg.\n\n"
                        f"TEKST:\n{tekst[:4000]}\n\nCOMPRESSIE:"
                    )

                    try:
                        chat = await self.client.chat.completions.create(
                            messages=[{"role": "user", "content": prompt}],
                            model=self.model,
                            temperature=0.2,
                        )
                        samenvatting = ((chat.choices[0].message.content or "") if chat.choices else "").strip()

                        if samenvatting and len(samenvatting) >= 10:
                            doc_hash = sc._doc_hash(tekst)
                            orig_tokens = sc._estimate_tokens(tekst)
                            sam_tokens = sc._estimate_tokens(samenvatting)

                            # Opslaan in shadow_summaries (excluded.* syntax)
                            conn.execute(
                                """INSERT INTO shadow_summaries
                                   (doc_id, doc_hash, samenvatting, origineel_tokens, samenvatting_tokens)
                                   VALUES (?, ?, ?, ?, ?)
                                   ON CONFLICT(doc_id)
                                   DO UPDATE SET doc_hash = excluded.doc_hash,
                                                samenvatting = excluded.samenvatting,
                                                origineel_tokens = excluded.origineel_tokens,
                                                samenvatting_tokens = excluded.samenvatting_tokens,
                                                aangemaakt = datetime('now')""",
                                (doc_id, doc_hash, samenvatting, orig_tokens, sam_tokens),
                            )
                            conn.commit()

                            bespaard = orig_tokens - sam_tokens
                            totaal_bespaard += bespaard
                            samengevat += 1
                            print(f"  {Kleur.GROEN}✓ {doc_id[:45]} ({orig_tokens}→{sam_tokens} tok){Kleur.RESET}")
                        else:
                            print(f"  {Kleur.GEEL}⊘ {doc_id[:45]} (leeg antwoord){Kleur.RESET}")

                    except Exception as e:
                        print(f"  {Kleur.ROOD}✗ {doc_id[:45]}: {e}{Kleur.RESET}")

                    # 3s interval (30 RPM op GROQ_API_KEY_OVERNIGHT)
                    await asyncio.sleep(3)
            finally:
                pass  # Connection reused via sc._get_summary_conn()

            # Log resultaten
            roi = sc.get_dividend_roi()

            if HAS_STACK:
                try:
                    stack = get_cortical_stack()
                    stack.log_event(
                        actor="dreamer",
                        action="shadow_summarization_rem",
                        details={
                            "samengevat": samengevat,
                            "kandidaten": len(candidates),
                            "totaal_bespaard": totaal_bespaard,
                            "roi": roi,
                        },
                    )
                    stack.flush()
                except Exception as e:
                    logger.debug("CorticalStack log failed: %s", e)

            print(
                f"{Kleur.GROEN}📑 Shadow summarization: {samengevat}/{len(candidates)} docs, "
                f"~{totaal_bespaard} tokens bespaard (ROI: {roi.get('roi_ratio', 0)}x){Kleur.RESET}"
            )

        except Exception as e:
            logger.debug("Shadow summarization error: %s", e)
            print(f"{Kleur.ROOD}📑 Shadow summarization error: {e}{Kleur.RESET}")

    async def _recursive_refine(self, drempel: int = 25, max_docs: int = 20) -> None:
        """Fase 31: Recursive Refiner — dubbele pers naar Super-Tokens.

        Samenvattingen die nog te veel tokens bevatten (>drempel) worden
        een tweede keer gecomprimeerd tot ~10 ultra-compacte Super-Tokens.
        Dit is de "dubbele pers" die ruis elimineert.

        Args:
            drempel: Samenvattingen boven deze tokengrens worden hergeperst.
            max_docs: Max documenten per cyclus.
        """
        print(f"{Kleur.GEEL}🔩 Recursive Refiner (dubbele pers)...{Kleur.RESET}")

        conn = None
        try:
            import sqlite3
            db_pad = str(Config.DATA_DIR / "cortical_stack.db")
            conn = sqlite3.connect(db_pad, timeout=Config.SQLITE_CONNECT_TIMEOUT)
            Config.apply_sqlite_perf(conn)

            # Zoek samenvattingen die nog te lang zijn
            kandidaten = conn.execute(
                """SELECT doc_id, samenvatting, samenvatting_tokens, origineel_tokens
                   FROM shadow_summaries
                   WHERE samenvatting_tokens > ?
                   ORDER BY samenvatting_tokens DESC
                   LIMIT ?""",
                (drempel, max_docs),
            ).fetchall()

            if not kandidaten:
                print(f"{Kleur.GROEN}🔩 Recursive Refiner: alle samenvattingen al compact.{Kleur.RESET}")
                return

            print(f"{Kleur.CYAAN}🔩 {len(kandidaten)} samenvattingen boven {drempel} tokens{Kleur.RESET}")

            verfijnd = 0
            totaal_bespaard = 0

            for doc_id, samenvatting, sam_tokens, orig_tokens in kandidaten:
                prompt = (
                    "Comprimeer deze samenvatting tot MAXIMAAL 10 woorden.\n"
                    "REGELS:\n"
                    "- Eén enkele zin, telegramstijl.\n"
                    "- Bewaar alleen kernfeiten en cijfers.\n"
                    "- Geen werkwoorden als het kan, geen lidwoorden.\n"
                    "- Antwoord ALLEEN met de super-compressie.\n\n"
                    f"SAMENVATTING:\n{samenvatting}\n\nSUPER-TOKEN:"
                )

                try:
                    chat = await self.client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model=self.model,
                        temperature=0.1,
                    )
                    super_token = ((chat.choices[0].message.content or "") if chat.choices else "").strip()

                    if super_token and len(super_token) >= 5:
                        nieuwe_tokens = max(1, len(super_token.split()))
                        bespaard = sam_tokens - nieuwe_tokens

                        # Alleen opslaan als het echt korter is
                        if nieuwe_tokens < sam_tokens:
                            conn.execute(
                                """UPDATE shadow_summaries
                                   SET samenvatting = ?,
                                       samenvatting_tokens = ?,
                                       aangemaakt = datetime('now')
                                   WHERE doc_id = ?""",
                                (super_token, nieuwe_tokens, doc_id),
                            )
                            totaal_bespaard += bespaard
                            verfijnd += 1
                            print(f"  {Kleur.GROEN}⚡ {doc_id[:45]} ({sam_tokens}→{nieuwe_tokens} tok){Kleur.RESET}")
                        else:
                            print(f"  {Kleur.GEEL}⊘ {doc_id[:45]} (al compact){Kleur.RESET}")
                    else:
                        print(f"  {Kleur.GEEL}⊘ {doc_id[:45]} (leeg antwoord){Kleur.RESET}")

                except Exception as e:
                    print(f"  {Kleur.ROOD}✗ {doc_id[:45]}: {e}{Kleur.RESET}")

                await asyncio.sleep(3)

            conn.commit()

            # Log naar CorticalStack
            if HAS_STACK and verfijnd > 0:
                try:
                    stack = get_cortical_stack()
                    stack.log_event(
                        actor="dreamer",
                        action="recursive_refine",
                        details={
                            "verfijnd": verfijnd,
                            "kandidaten": len(kandidaten),
                            "totaal_bespaard": totaal_bespaard,
                        },
                    )
                    stack.flush()
                except Exception as e:
                    logger.debug("CorticalStack log failed: %s", e)

            print(
                f"{Kleur.GROEN}🔩 Recursive Refiner: {verfijnd}/{len(kandidaten)} "
                f"hergeperst, ~{totaal_bespaard} extra tokens bespaard{Kleur.RESET}"
            )

        except Exception as e:
            logger.debug("Recursive Refiner error: %s", e)
            print(f"{Kleur.ROOD}🔩 Recursive Refiner error: {e}{Kleur.RESET}")
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception as e:
                    logger.debug("DB close error: %s", e)

    async def _research_failures(self) -> None:
        """Research top failure topics via VoidWalker."""
        try:
            from danny_toolkit.brain.black_box import get_black_box
            from danny_toolkit.brain.void_walker import VoidWalker
            bb = get_black_box()
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
