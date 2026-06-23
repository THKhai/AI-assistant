from llama_index.core import VectorStoreIndex, StorageContext

from src.core import config
from src.core.embedder import get_embedder
from src.core.llm import get_llm
from src.core.vector_store import get_vector_store

_index = None


def _get_index() -> VectorStoreIndex:
    global _index
    if _index is None:
        vector_store = get_vector_store()
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        _index = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context,
            embed_model=get_embedder(),
        )
    return _index


def ask(question: str, history: list[dict] = None) -> dict:
    index = _get_index()
    query_engine = index.as_query_engine(
        llm=get_llm(),
        similarity_top_k=config.RETRIEVAL_TOP_K,
    )

    if history:
        history_text = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in history[-config.CONVERSATION_HISTORY_TURNS * 2:]
        )
        augmented_question = f"Conversation so far:\n{history_text}\n\nNew question: {question}"
    else:
        augmented_question = question

    response = query_engine.query(augmented_question)

    sources = []
    for node in response.source_nodes:
        title = node.metadata.get("title", "")
        if title and title not in sources:
            sources.append(title)

    return {
        "answer": str(response),
        "sources": sources,
    }


def invalidate_index():
    global _index
    _index = None
