import os
from glob import glob
import streamlit as st
from qdrant_client import QdrantClient
from backend.ingest import main as ingest_main

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "documents")

st.set_page_config(page_title="RAG Index Manager", page_icon="📚")

st.title("📚 RAG Index Manager (TXT Files)")

st.write("Manage and index `.txt` documents for the RAG system.")

# -----------------------------
# Show TXT files
# -----------------------------
st.subheader("📂 TXT Files in `/data`")

data_dir = "data"
txt_files = glob(os.path.join(data_dir, "*.txt"))

if not txt_files:
    st.info("No `.txt` files found. Place them in `./data` on the host machine.")
else:
    for f in txt_files:
        st.write(f"- `{os.path.basename(f)}`")

# -----------------------------
# Run ingestion
# -----------------------------
st.subheader("📥 Indexing")

if st.button("Rebuild Qdrant index from TXT files"):
    with st.spinner("Reading + chunking + embedding `.txt` files..."):
        ingest_main()
    st.success("Done! TXT files indexed into Qdrant.")


# -----------------------------
# Show Qdrant status
# -----------------------------
st.subheader("🧠 Qdrant Status")

try:
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    collections = client.get_collections()
    names = [c.name for c in collections.collections]

    st.write("Collections:", names or ["none"])

    if COLLECTION_NAME in names:
        info = client.get_collection(COLLECTION_NAME)
        st.write(f"Collection `{COLLECTION_NAME}` details:")
        st.json(info.dict())

except Exception as e:
    st.error("Cannot connect to Qdrant.")
    st.exception(e)
