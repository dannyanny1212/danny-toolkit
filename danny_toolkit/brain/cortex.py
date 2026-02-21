import logging
import os
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Robuuste .env loader — vindt altijd de project root
try:
    from dotenv import load_dotenv
    _root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    load_dotenv(
        dotenv_path=os.path.join(_root, ".env"),
        override=True,
    )
except ImportError:
    pass

from groq import AsyncGroq
from danny_toolkit.core.utils import Kleur

# Optionele dependencies
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    nx = None
    HAS_NETWORKX = False

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

try:
    from danny_toolkit.brain.unified_memory import UnifiedMemory
    HAS_VECTOR = True
except ImportError:
    HAS_VECTOR = False


@dataclass
class Triple:
    """Een kennisrelatie: subject → predicaat → object."""
    subject: str
    predicaat: str
    object: str
    confidence: float = 0.5
    bron: str = "system"


@dataclass
class Entity:
    """Een entiteit in de kennisgraaf."""
    naam: str
    type: str = "onbekend"
    beschrijving: str = ""
    mention_count: int = 1


class TheCortex:
    """
    THE CORTEX (Invention #17)
    --------------------------
    Knowledge Graph overlay op bestaande RAG.

    Bouwt een associatief geheugen via entity-relatie triples.
    Combineert vector search met graph traversal voor
    diepere context retrieval.

    Features:
    - LLM-gestuurde triple extractie uit tekst
    - SQLite-persistentie op CorticalStack DB
    - NetworkX in-memory graaf voor snelle traversal
    - Hybrid search: vector similarity + graph expansion
    - NeuralBus integratie voor live updates
    """

    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "mixtral-8x7b-32768"

        # In-memory graaf (NetworkX)
        self._graph = nx.DiGraph() if HAS_NETWORKX else None

        # CorticalStack koppeling
        self._stack = get_cortical_stack() if HAS_STACK else None

        # NeuralBus koppeling
        self._bus = get_bus() if HAS_BUS else None

        # SQLite tabellen aanmaken
        if self._stack:
            self._ensure_tables()
            self._build_graph()

    def _ensure_tables(self):
        """Maak entities + knowledge_graph tabellen op CorticalStack DB."""
        if not self._stack:
            return
        try:
            self._stack._conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    naam TEXT UNIQUE NOT NULL,
                    type TEXT DEFAULT 'onbekend',
                    beschrijving TEXT DEFAULT '',
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    mention_count INTEGER DEFAULT 1
                )
            """)
            self._stack._conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_graph (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_a TEXT NOT NULL,
                    relatie TEXT NOT NULL,
                    entity_b TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    bron TEXT DEFAULT 'system',
                    learned_at TEXT NOT NULL,
                    UNIQUE(entity_a, relatie, entity_b)
                )
            """)
            # Indexes voor snelle graph traversal
            self._stack._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kg_entity_a
                ON knowledge_graph(entity_a)
            """)
            self._stack._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kg_entity_b
                ON knowledge_graph(entity_b)
            """)
            self._stack._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_mention
                ON entities(mention_count DESC)
            """)
            self._stack._conn.commit()
        except Exception as e:
            print(f"{Kleur.ROOD}[Cortex] Tabel-fout: {e}{Kleur.RESET}")

    def _build_graph(self):
        """Laad alle triples uit SQLite in NetworkX graaf."""
        if self._graph is None or not self._stack:
            return
        try:
            rows = self._stack._conn.execute(
                "SELECT entity_a, relatie, entity_b, confidence FROM knowledge_graph"
            ).fetchall()
            for row in rows:
                self._graph.add_edge(
                    row[0], row[2],
                    relatie=row[1],
                    confidence=row[3],
                )
            print(
                f"{Kleur.CYAAN}[Cortex] Graaf geladen: "
                f"{self._graph.number_of_nodes()} nodes, "
                f"{self._graph.number_of_edges()} edges{Kleur.RESET}"
            )
        except Exception as e:
            print(f"{Kleur.ROOD}[Cortex] Build-fout: {e}{Kleur.RESET}")

    async def extract_triples(self, text: str) -> List[Triple]:
        """Extraheer kennisrelaties uit tekst via LLM."""
        prompt = (
            "Extract knowledge triples (subject, predicate, object) from this text.\n"
            "Return ONLY a JSON array of objects with keys: subject, predicate, object.\n"
            "Max 10 triples. Be precise and factual.\n\n"
            f"Text: {text[:2000]}"
        )
        try:
            chat = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.2,
            )
            raw = chat.choices[0].message.content

            # Parse JSON uit response
            import json
            # Strip markdown code fences als aanwezig
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1]
                clean = clean.rsplit("```", 1)[0]

            items = json.loads(clean)
            triples = []
            for item in items:
                if all(k in item for k in ("subject", "predicate", "object")):
                    triples.append(Triple(
                        subject=item["subject"].lower().strip(),
                        predicaat=item["predicate"].lower().strip(),
                        object=item["object"].lower().strip(),
                        confidence=0.7,
                        bron="llm_extraction",
                    ))
            return triples
        except Exception as e:
            print(f"{Kleur.ROOD}[Cortex] Extractie-fout: {e}{Kleur.RESET}")
            return []

    def add_triple(
        self,
        entity_a: str,
        relatie: str,
        entity_b: str,
        confidence: float = 0.5,
        bron: str = "system",
    ):
        """Sla een triple op in SQLite + sync naar NetworkX."""
        now = datetime.now().isoformat()

        if self._stack:
            try:
                # Upsert entities
                for naam in (entity_a, entity_b):
                    self._stack._conn.execute("""
                        INSERT INTO entities (naam, first_seen, last_seen, mention_count)
                        VALUES (?, ?, ?, 1)
                        ON CONFLICT(naam) DO UPDATE SET
                            last_seen = excluded.last_seen,
                            mention_count = mention_count + 1
                    """, (naam, now, now))

                # Insert triple
                self._stack._conn.execute("""
                    INSERT INTO knowledge_graph (entity_a, relatie, entity_b, confidence, bron, learned_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(entity_a, relatie, entity_b) DO UPDATE SET
                        confidence = MAX(confidence, excluded.confidence),
                        learned_at = excluded.learned_at
                """, (entity_a, relatie, entity_b, confidence, bron, now))

                self._stack._conn.commit()
            except Exception as e:
                print(f"{Kleur.ROOD}[Cortex] Write-fout: {e}{Kleur.RESET}")

        # Sync naar NetworkX
        if self._graph is not None:
            self._graph.add_edge(
                entity_a, entity_b,
                relatie=relatie,
                confidence=confidence,
            )

        # Publiceer op NeuralBus
        if self._bus and HAS_BUS:
            try:
                self._bus.publish(
                    EventTypes.KNOWLEDGE_GRAPH_UPDATE,
                    {
                        "entity_a": entity_a,
                        "relatie": relatie,
                        "entity_b": entity_b,
                        "confidence": confidence,
                    },
                    bron="cortex",
                )
            except Exception as e:
                logger.debug("NeuralBus publish error: %s", e)

    def find_related(
        self,
        entity: str,
        depth: int = 2,
        min_confidence: float = 0.3,
    ) -> List[str]:
        """BFS graph traversal — vind gerelateerde entiteiten."""
        if self._graph is None or entity not in self._graph:
            # Fallback: SQLite-only query
            return self._find_related_sql(entity, min_confidence)

        try:
            nearby = nx.single_source_shortest_path_length(
                self._graph, entity, cutoff=depth
            )
            # Filter op confidence
            results = []
            for node, dist in nearby.items():
                if node == entity:
                    continue
                # Check edge confidence op pad
                if dist == 1:
                    edge = self._graph.edges[entity, node]
                    if edge.get("confidence", 0) >= min_confidence:
                        results.append(node)
                else:
                    results.append(node)
            return results
        except Exception as e:
            logger.debug("Graph traversal error: %s", e)
            return []

    def _find_related_sql(
        self,
        entity: str,
        min_confidence: float = 0.3,
    ) -> List[str]:
        """Fallback: zoek gerelateerde entiteiten via pure SQL."""
        if not self._stack:
            return []
        try:
            rows = self._stack._conn.execute("""
                SELECT entity_b FROM knowledge_graph
                WHERE entity_a = ? AND confidence >= ?
                UNION
                SELECT entity_a FROM knowledge_graph
                WHERE entity_b = ? AND confidence >= ?
            """, (entity, min_confidence, entity, min_confidence)).fetchall()
            return [row[0] for row in rows]
        except Exception:
            return []

    def get_entity_context(self, entity: str) -> str:
        """Alle relaties rond een entiteit als leesbare tekst."""
        if not self._stack:
            return ""
        try:
            rows = self._stack._conn.execute("""
                SELECT entity_a, relatie, entity_b, confidence
                FROM knowledge_graph
                WHERE entity_a = ? OR entity_b = ?
                ORDER BY confidence DESC
                LIMIT 20
            """, (entity, entity)).fetchall()

            if not rows:
                return ""

            lines = [f"[KENNISGRAAF: {entity}]"]
            for row in rows:
                lines.append(
                    f"- {row[0]} --[{row[1]}]--> {row[2]} "
                    f"(conf: {row[3]:.1f})"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.debug("Entity context error: %s", e)
            return ""

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Gecombineerde search: vector similarity + graph expansion.

        1. Extraheer entiteiten uit query
        2. Zoek graph-buren van gevonden entiteiten
        3. Combineer met vector search resultaten
        """
        results = []

        # Stap 1: Zoek entiteiten in de query
        graph_context = []
        if self._stack:
            try:
                # Zoek welke bekende entiteiten in de query voorkomen
                all_entities = self._stack._conn.execute(
                    "SELECT naam FROM entities ORDER BY mention_count DESC LIMIT 200"
                ).fetchall()
                matched = [
                    row[0] for row in all_entities
                    if row[0].lower() in query.lower()
                ]

                # Stap 2: Expandeer via graph
                for ent in matched[:3]:
                    related = self.find_related(ent, depth=2)
                    context = self.get_entity_context(ent)
                    if context:
                        graph_context.append(context)
                    for rel in related[:5]:
                        ctx = self.get_entity_context(rel)
                        if ctx:
                            graph_context.append(ctx)
            except Exception as e:
                logger.debug("Entity expansion error: %s", e)

        # Stap 3: Combineer resultaten
        if graph_context:
            results.append({
                "bron": "knowledge_graph",
                "content": "\n\n".join(graph_context[:top_k]),
                "score": 0.8,
            })

        return results

    def get_stats(self) -> Dict:
        """Node/edge counts van NetworkX + entity/triple counts van SQLite."""
        stats = {
            "graph_nodes": 0,
            "graph_edges": 0,
            "db_entities": 0,
            "db_triples": 0,
            "has_networkx": HAS_NETWORKX,
            "has_stack": HAS_STACK,
        }

        if self._graph:
            stats["graph_nodes"] = self._graph.number_of_nodes()
            stats["graph_edges"] = self._graph.number_of_edges()

        if self._stack:
            try:
                stats["db_entities"] = self._stack._conn.execute(
                    "SELECT COUNT(*) FROM entities"
                ).fetchone()[0]
                stats["db_triples"] = self._stack._conn.execute(
                    "SELECT COUNT(*) FROM knowledge_graph"
                ).fetchone()[0]
            except Exception as e:
                logger.debug("Stats DB error: %s", e)

        return stats
