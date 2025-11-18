import os
from typing import List, Optional

from openai import OpenAI
from qdrant_client import QdrantClient
from langfuse import Langfuse


# ============================================================
# Environment & Clients
# ============================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "documents")

LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")

client = OpenAI(api_key=OPENAI_API_KEY)
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

langfuse: Optional[Langfuse] = (
    Langfuse(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_HOST,
    )
    if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
    else None
)


# ============================================================
# Embedding
# ============================================================
def embed_text(text: str) -> List[float]:
    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return resp.data[0].embedding


# ============================================================
# Retrieval (correct for qdrant-client 1.16.0)
# ============================================================
def semantic_search(query: str, top_k: int = 5):
    vector = embed_text(query)
    res = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=top_k,
        with_payload=True,
    )
    return list(res.points)


# ============================================================
# Prompt construction
# ============================================================
def build_prompt(query: str, retrieved_chunks: List[str], history: List[dict]):
    context = "\n\n---\n\n".join(retrieved_chunks)

    history_text = ""
    for h in history:
        history_text += f"{h['role'].upper()}: {h['content']}\n"

    return f"""
Use ONLY the provided context. If the answer is not explicitly in the context,
reply with "I don't know".

Conversation:
{history_text}

Context:
{context}

Question: {query}
""".strip()


# ============================================================
# RAG pipeline (Langfuse v2)
# ============================================================
def answer_with_rag(
    user_id: str,
    session_id: str,
    query: str,
    history: List[dict]
) -> str:

    # Retrieve chunks
    points = semantic_search(query, top_k=5)
    chunks = [p.payload.get("text", "") for p in points]

    # Build prompt
    prompt = build_prompt(query, chunks, history)

    # Initialize Langfuse trace
    trace = generation = None
    if langfuse:
        trace = langfuse.trace(
            name="chat_trace",
            user_id=user_id,
            session_id=session_id,
            metadata={"query": query},
        )

        # 🔥 Log chunks safely using metadata update
        trace.update(
            metadata={
                "retrieved_chunks": chunks,
                "num_chunks": len(chunks),
            }
        )

        generation = trace.generation(
            name="rag_generation",
            model=CHAT_MODEL,
            input=prompt,
        )

    # Call model
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )

    answer = resp.choices[0].message.content

    # Finalize Langfuse logs
    if generation:
        generation.end(output=answer)

    if trace:
        trace.update(output=answer)

    return answer
