"""
RAG Search Web Terminal — Streamlit UI voor vector store zoeken.
Poort 8501 | Start: venv311/Scripts/python.exe -m streamlit run rag_search_ui.py --server.port 8501
"""

import sys
import os
from pathlib import Path

# Project root op sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

import streamlit as st

# --- Page config ---
st.set_page_config(
    page_title="Omega RAG Search",
    page_icon="🔍",
    layout="wide",
)

# --- Store definities ---
STORES = {
    "Brain Memory (unified_vectors.json)": ROOT / "data" / "brain_memory" / "unified_vectors.json",
    "RAG Documenten (vector_db.json)": ROOT / "data" / "rag" / "vector_db.json",
    "Knowledge Companion": ROOT / "data" / "knowledge_companion_vectors.json",
    "Legendary Companion": ROOT / "data" / "legendary_companion_vectors.json",
}


@st.cache_resource
def load_embedder():
    """Laad embedding provider (eenmalig, cached)."""
    from danny_toolkit.core.embeddings import get_embedder
    return get_embedder(gebruik_voyage=True, gebruik_cache=True)


def load_store(db_file: Path):
    """Laad een VectorStore voor het gegeven bestand."""
    from danny_toolkit.core.vector_store import VectorStore
    embedder = load_embedder()
    return VectorStore(embedding_provider=embedder, db_file=db_file)


# --- Sidebar ---
st.sidebar.title("⚙️ Instellingen")

store_naam = st.sidebar.selectbox("Vector Store", list(STORES.keys()))
db_path = STORES[store_naam]

top_k = st.sidebar.slider("Top K resultaten", min_value=1, max_value=20, value=5)
min_score = st.sidebar.slider("Minimum score", min_value=0.0, max_value=1.0, value=0.0, step=0.05)

# Store stats
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Store Info")

if db_path.exists():
    store = load_store(db_path)
    stats = store.statistieken()
    st.sidebar.metric("Documenten", stats["totaal_documenten"])
    st.sidebar.metric("Embedding dim", stats.get("embedding_dimensies", "N/A"))
    st.sidebar.metric("Queries uitgevoerd", stats["queries_uitgevoerd"])
    if stats.get("db_grootte_bytes", 0) > 0:
        grootte_mb = stats["db_grootte_bytes"] / (1024 * 1024)
        st.sidebar.metric("DB grootte", f"{grootte_mb:.1f} MB")
else:
    st.sidebar.warning(f"Store niet gevonden: {db_path.name}")
    store = None

# --- Main ---
st.title("🔍 Omega RAG Search Terminal")
st.caption(f"Store: `{db_path}`")

query = st.text_input("Zoekquery", placeholder="Typ je zoekopdracht...")

if query and store:
    with st.spinner("Zoeken..."):
        resultaten = store.zoek(query, top_k=top_k, min_score=min_score)

    if resultaten:
        st.success(f"**{len(resultaten)}** resultaten gevonden (top {top_k}, min score {min_score})")

        for i, res in enumerate(resultaten, 1):
            score_pct = res["score"] * 100
            # Kleur op basis van score
            if res["score"] >= 0.8:
                score_color = "🟢"
            elif res["score"] >= 0.5:
                score_color = "🟡"
            else:
                score_color = "🔴"

            with st.container():
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    st.markdown(f"### {score_color} #{i} — `{res['id']}`")
                with col2:
                    st.metric("Score", f"{score_pct:.1f}%")

                # Tekst preview (max 500 chars)
                tekst = res["tekst"]
                if len(tekst) > 500:
                    st.text(tekst[:500] + "...")
                else:
                    st.text(tekst)

                # Metadata expander
                if res.get("metadata"):
                    with st.expander("📋 Metadata"):
                        st.json(res["metadata"])

                st.divider()
    else:
        st.warning("Geen resultaten gevonden. Probeer een andere query of verlaag de minimum score.")

elif query and not store:
    st.error("Kan niet zoeken — vector store niet geladen.")
