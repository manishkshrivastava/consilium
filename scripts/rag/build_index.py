"""
Step 5: Build RAG Vector Index from 3GPP Documents
- Chunks 3GPP markdown documents
- Generates embeddings using sentence-transformers
- Stores in ChromaDB for fast retrieval
"""

import os
import sys
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "data" / "raw" / "tspec_llm" / "3GPP-clean"
CHROMA_DIR = PROJECT_ROOT / "rag" / "vector_db" / "chroma_3gpp"

# Embedding model — small but effective, runs locally on MPS
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Chunking config
CHUNK_SIZE = 512       # tokens per chunk
CHUNK_OVERLAP = 50     # overlap between chunks
MAX_FILES = None       # Set to a number to limit (e.g., 500 for testing)


def main():
    print("=" * 60)
    print("TELCO SLM — Step 5: Building RAG Vector Index")
    print("=" * 60)

    if not DOCS_DIR.exists():
        print(f"ERROR: 3GPP docs not found at {DOCS_DIR}")
        sys.exit(1)

    # Collect markdown files
    md_files = sorted(DOCS_DIR.rglob("*.md"))
    if MAX_FILES:
        md_files = md_files[:MAX_FILES]

    print(f"\n  Documents found: {len(md_files)}")
    print(f"  Embedding model: {EMBEDDING_MODEL}")
    print(f"  Chunk size: {CHUNK_SIZE} tokens")
    print(f"  Chunk overlap: {CHUNK_OVERLAP} tokens")
    print(f"  Index path: {CHROMA_DIR}")

    # Setup LlamaIndex
    from llama_index.core import (
        SimpleDirectoryReader,
        VectorStoreIndex,
        StorageContext,
        Settings,
        Document,
    )
    from llama_index.core.node_parser import SentenceSplitter
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore
    import chromadb

    # Configure embedding model
    print(f"\n[1/4] Loading embedding model...")
    embed_model = HuggingFaceEmbedding(
        model_name=EMBEDDING_MODEL,
        device="mps",  # Use Apple Silicon GPU
    )
    Settings.embed_model = embed_model
    Settings.chunk_size = CHUNK_SIZE
    Settings.chunk_overlap = CHUNK_OVERLAP

    # Load documents
    print(f"\n[2/4] Loading {len(md_files)} documents...")
    documents = []
    skipped = 0
    for i, md_file in enumerate(md_files):
        try:
            with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Skip very short documents (< 100 chars) and README files
            if len(content) < 100 or md_file.name == "README.md":
                skipped += 1
                continue

            # Extract metadata from path
            # e.g., 3GPP-clean/Rel-15/38_series/38211-f40.md
            parts = md_file.relative_to(DOCS_DIR).parts
            release = parts[0] if len(parts) > 0 else "unknown"
            series = parts[1] if len(parts) > 1 else "unknown"
            spec_name = md_file.stem

            doc = Document(
                text=content,
                metadata={
                    "release": release,
                    "series": series,
                    "spec": spec_name,
                    "filename": md_file.name,
                    "source": str(md_file.relative_to(DOCS_DIR)),
                },
            )
            documents.append(doc)

        except Exception as e:
            skipped += 1
            continue

        if (i + 1) % 1000 == 0:
            print(f"    Loaded {i+1}/{len(md_files)} files ({len(documents)} docs, {skipped} skipped)")

    print(f"  Total documents loaded: {len(documents)} ({skipped} skipped)")

    # Setup ChromaDB
    print(f"\n[3/4] Setting up ChromaDB...")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    chroma_collection = chroma_client.get_or_create_collection(
        name="telco_3gpp",
        metadata={"description": "3GPP specifications Release 8-19"},
    )
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Build index
    print(f"\n[4/4] Building vector index (this takes a while)...")
    print(f"  Chunking {len(documents)} documents and generating embeddings...")
    start_time = time.time()

    # Process in batches to show progress
    BATCH_SIZE = 200
    for batch_start in range(0, len(documents), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(documents))
        batch_docs = documents[batch_start:batch_end]

        if batch_start == 0:
            index = VectorStoreIndex.from_documents(
                batch_docs,
                storage_context=storage_context,
                show_progress=True,
            )
        else:
            for doc in batch_docs:
                index.insert(doc)

        elapsed = time.time() - start_time
        docs_per_sec = (batch_end) / elapsed if elapsed > 0 else 0
        eta = (len(documents) - batch_end) / docs_per_sec if docs_per_sec > 0 else 0
        print(f"  Indexed {batch_end}/{len(documents)} docs ({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)")

    total_time = time.time() - start_time

    # Stats
    print(f"\n{'='*60}")
    print(f"RAG Index Built Successfully!")
    print(f"{'='*60}")
    print(f"  Documents indexed: {len(documents)}")
    print(f"  Vectors in ChromaDB: {chroma_collection.count()}")
    print(f"  Index location: {CHROMA_DIR}")
    print(f"  Time: {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"\n  Next: python scripts/rag/query_rag.py")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
