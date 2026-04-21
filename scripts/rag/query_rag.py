"""
RAG Query Pipeline: Retrieve 3GPP context + Generate with TelcoGPT v3
- Retrieves relevant chunks from ChromaDB
- Feeds context to fine-tuned TelcoGPT
- Compares: base model vs fine-tuned vs fine-tuned+RAG
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DIR = PROJECT_ROOT / "rag" / "vector_db" / "chroma_3gpp"
ADAPTER_PATH = PROJECT_ROOT / "models" / "telco-slm-v3-mlx" / "adapter"
BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

TOP_K = 5  # Number of chunks to retrieve


def setup_rag():
    """Initialize RAG components."""
    from llama_index.core import VectorStoreIndex, StorageContext, Settings
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore
    import chromadb

    # Embedding model
    embed_model = HuggingFaceEmbedding(
        model_name=EMBEDDING_MODEL,
        device="mps",
    )
    Settings.embed_model = embed_model

    # Load ChromaDB
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    chroma_collection = chroma_client.get_collection("telco_3gpp")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    # Create index from existing store
    index = VectorStoreIndex.from_vector_store(vector_store)

    return index


def retrieve_context(index, query: str, top_k: int = TOP_K) -> str:
    """Retrieve relevant 3GPP chunks for a query."""
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)

    context_parts = []
    sources = []
    for node in nodes:
        context_parts.append(node.text[:500])  # Cap each chunk
        meta = node.metadata
        sources.append(f"{meta.get('release', '?')}/{meta.get('series', '?')}/{meta.get('spec', '?')}")

    context = "\n\n---\n\n".join(context_parts)
    return context, sources


def generate_with_rag(model, tokenizer, query: str, context: str) -> str:
    """Generate response using TelcoGPT with RAG context."""
    from mlx_lm import generate

    system_prompt = (
        "You are TelcoGPT, an expert AI assistant specialized in telecommunications. "
        "You have deep knowledge of 3GPP standards, 5G/LTE network operations, "
        "RAN optimization, core network, transport, IMS/VoLTE, and network security.\n\n"
        "IMPORTANT RULES:\n"
        "- NEVER copy raw tables from the reference material\n"
        "- ALWAYS explain concepts in your own words using plain language\n"
        "- Give practical, actionable answers that a network engineer can use\n"
        "- Structure your response with numbered steps or bullet points\n"
        "- If the reference material is not relevant to the question, use your own knowledge instead\n"
        "- Focus on HOW TO do things, not just what the standard says"
    )

    user_prompt = f"""I have some 3GPP reference material that may be helpful. Use it as background knowledge, but answer in your own words with practical guidance.

Reference Material (use as background, do NOT copy directly):
{context}

Question: {query}

Give a clear, practical, step-by-step answer that a network engineer can act on."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    response = generate(model, tokenizer, prompt=text, max_tokens=500, verbose=False)
    return response


def generate_without_rag(model, tokenizer, query: str) -> str:
    """Generate response using TelcoGPT WITHOUT RAG context."""
    from mlx_lm import generate

    system_prompt = (
        "You are TelcoGPT, an expert AI assistant specialized in telecommunications. "
        "You have deep knowledge of 3GPP standards, 5G/LTE network operations, "
        "RAN optimization, core network, transport, IMS/VoLTE, and network security."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    response = generate(model, tokenizer, prompt=text, max_tokens=500, verbose=False)
    return response


def main():
    print("=" * 60)
    print("TELCO SLM — RAG Query Pipeline")
    print("=" * 60)

    if not CHROMA_DIR.exists():
        print("ERROR: Vector index not found. Run build_index.py first.")
        sys.exit(1)

    # Setup
    print("\nLoading RAG index...")
    index = setup_rag()

    print("Loading TelcoGPT v3...")
    from mlx_lm import load
    model, tokenizer = load(BASE_MODEL, adapter_path=str(ADAPTER_PATH))

    # Test queries
    test_queries = [
        "What is the purpose of SSB (Synchronization Signal Block) in 5G NR?",
        "Explain the N4 interface between SMF and UPF in 5G core.",
        "What are the QoS parameters for 5QI value 1 (conversational voice)?",
        "How does the 5G registration procedure work?",
        "What is network slicing and how is S-NSSAI structured?",
    ]

    print(f"\nRunning {len(test_queries)} test queries...\n")

    for i, query in enumerate(test_queries):
        print(f"{'='*60}")
        print(f"Q{i+1}: {query}")
        print(f"{'='*60}")

        # Retrieve context
        context, sources = retrieve_context(index, query)
        print(f"\n📚 Retrieved from: {', '.join(sources[:3])}")

        # Generate with RAG
        print(f"\n🔵 TelcoGPT v3 + RAG:")
        rag_response = generate_with_rag(model, tokenizer, query, context)
        print(rag_response[:500])

        # Generate without RAG
        print(f"\n🔴 TelcoGPT v3 (no RAG):")
        no_rag_response = generate_without_rag(model, tokenizer, query)
        print(no_rag_response[:500])

        print()

    # Interactive mode
    print(f"\n{'='*60}")
    print("Interactive RAG mode (type 'quit' to exit)")
    print(f"{'='*60}")

    while True:
        try:
            query = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue

        context, sources = retrieve_context(index, query)
        print(f"\n📚 Sources: {', '.join(sources[:3])}")

        response = generate_with_rag(model, tokenizer, query, context)
        print(f"\nTelcoGPT+RAG: {response}")


if __name__ == "__main__":
    main()
