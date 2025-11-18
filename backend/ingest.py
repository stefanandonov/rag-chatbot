import os
from glob import glob
from uuid import uuid4
from typing import List

from tqdm import tqdm                               # ✅ NEW

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI


# -----------------------------
# Environment configuration
# -----------------------------
DATA_DIR = os.getenv("DATA_DIR", "data")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "documents")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


# -----------------------------
# Helper functions
# -----------------------------
def load_text_file(path: str) -> str:
    """Load content from a TXT file."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def embed_batch(texts: List[str]):
    """Embed a batch of chunks using OpenAI embeddings."""
    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in resp.data]


def ensure_collection(dim: int):
    """Create Qdrant collection if it does not exist yet."""
    existing = qdrant.get_collections().collections
    existing_names = [c.name for c in existing]

    if COLLECTION_NAME not in existing_names:
        print("🆕 Creating Qdrant collection...")
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=dim,
                distance=Distance.COSINE
            ),
        )


# -----------------------------
# Main ingestion function
# -----------------------------
def main():
    txt_paths = glob(os.path.join(DATA_DIR, "*.txt"))

    if not txt_paths:
        print("⚠️ No TXT files found in `/data` directory.")
        return

    print(f"📄 Found {len(txt_paths)} TXT files.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=200,
    )

    all_chunks = []

    # ---------------------------
    # Load + Chunk with tqdm
    # ---------------------------
    print("\n📥 Loading + chunking TXT files...")
    for file_path in tqdm(txt_paths, desc="Chunking files", unit="file"):
        text = load_text_file(file_path)

        chunks = splitter.split_text(text)

        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "text": chunk,
                "source": os.path.basename(file_path),
                "chunk_idx": i,
            })

    print(f"\n🧩 Total text chunks extracted: {len(all_chunks)}")

    # ---------------------------
    # Embeddings with tqdm
    # ---------------------------
    print("\n🧠 Computing embeddings... (this may take a moment)")
    texts = [c["text"] for c in all_chunks]

    # tqdm wrapper for embedding step (single batch)
    vectors = []
    batch_size = 256  # adjustable
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
        batch = texts[i:i + batch_size]
        vectors.extend(embed_batch(batch))

    dim = len(vectors[0])
    ensure_collection(dim)

    # ---------------------------
    # Prepare points with tqdm
    # ---------------------------
    print("\n📦 Preparing Qdrant points...")
    points = []
    for vector, payload in tqdm(zip(vectors, all_chunks), total=len(all_chunks), desc="Building points"):
        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload=payload,
            )
        )

    # ---------------------------
    # Upload to Qdrant with tqdm
    # ---------------------------
    print("\n🚀 Uploading to Qdrant...")

    # If number of points is huge, upload in chunks with tqdm
    upload_batch = 500
    for i in tqdm(range(0, len(points), upload_batch), desc="Uploading batches"):
        batch = points[i:i + upload_batch]
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=batch,
        )

    print(f"\n✅ Finished ingesting {len(points)} text chunks into Qdrant collection `{COLLECTION_NAME}`.")


if __name__ == "__main__":
    main()
