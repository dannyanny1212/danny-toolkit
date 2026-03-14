"""
Omega RAG Search Terminal — Streamlit UI voor ChromaDB zoeken.
Poort 8501 | Start: venv311/Scripts/python.exe -m streamlit run rag_search_ui.py --server.port 8501
"""

from __future__ import annotations

import logging
import sys
import os
from pathlib import Path

logger = logging.getLogger(__name__)

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

CHROMA_DIR = str(ROOT / "data" / "rag" / "chromadb")


@st.cache_resource
def load_chroma_client() -> object:
    """Laad ChromaDB PersistentClient (eenmalig, cached)."""
    try:
        import chromadb
    except ImportError:
        logger.debug("chromadb not available")
        return None
    return chromadb.PersistentClient(path=CHROMA_DIR)


@st.cache_resource
def get_collection_names() -> dict[str, int]:
    """Haal alle collectie-namen op."""
    client = load_chroma_client()
    collections = client.list_collections()
    return {col.name: col.count() for col in collections}


def get_collection(name: str) -> object:
    """Haal een specifieke collectie op."""
    client = load_chroma_client()
    return client.get_collection(name=name)


# --- Sidebar ---
st.sidebar.title("⚙️ Instellingen")

collections_info = get_collection_names()
# Sorteer: danny_knowledge eerst (de hoofdcollectie)
sorted_names = sorted(collections_info.keys(), key=lambda x: (x != "danny_knowledge", x))
col_labels = {name: f"{name} ({count} docs)" for name, count in collections_info.items()}

selected_col = st.sidebar.selectbox(
    "ChromaDB Collectie",
    sorted_names,
    format_func=lambda x: col_labels[x],
)

top_k = st.sidebar.slider("Top K resultaten", min_value=1, max_value=20, value=5)

# Store stats
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Collectie Info")

doc_count = collections_info.get(selected_col, 0)
st.sidebar.metric("Documenten", doc_count)

chroma_db_path = Path(CHROMA_DIR) / "chroma.sqlite3"
if chroma_db_path.exists():
    grootte_mb = chroma_db_path.stat().st_size / (1024 * 1024)
    st.sidebar.metric("DB grootte", f"{grootte_mb:.1f} MB")

st.sidebar.metric("Collecties totaal", len(collections_info))

# --- Main ---
st.title("🔍 Omega RAG Search Terminal")
st.caption(f"ChromaDB: `{CHROMA_DIR}` | Collectie: `{selected_col}`")

query = st.text_input("Zoekquery", placeholder="Typ je zoekopdracht...")

if query and doc_count > 0:
    with st.spinner("Zoeken in ChromaDB..."):
        collection = get_collection(selected_col)
        n_results = min(top_k, doc_count)
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    docs = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0] if results["metadatas"] else []
    dists = results["distances"][0] if results["distances"] else []
    ids = results["ids"][0] if results["ids"] else []

    if docs:
        st.success(f"**{len(docs)}** resultaten gevonden (top {top_k})")

        for i, (doc, meta, dist, doc_id) in enumerate(zip(docs, metas, dists, ids), 1):
            # ChromaDB distance: lager = beter. Convert naar similarity score.
            # Cosine distance: score = 1 - distance
            score = max(0.0, 1.0 - dist)
            score_pct = score * 100

            if score >= 0.8:
                score_color = "🟢"
            elif score >= 0.5:
                score_color = "🟡"
            else:
                score_color = "🔴"

            with st.container():
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    st.markdown(f"### {score_color} #{i} — `{doc_id}`")
                with col2:
                    st.metric("Score", f"{score_pct:.1f}%")

                # Tekst preview
                if len(doc) > 500:
                    st.text(doc[:500] + "...")
                else:
                    st.text(doc)

                # Metadata expander
                if meta:
                    with st.expander("📋 Metadata"):
                        st.json(meta)

                st.divider()
    else:
        st.warning("Geen resultaten gevonden.")

elif query and doc_count == 0:
    st.error(f"Collectie '{selected_col}' is leeg.")
