from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from src.core import config

_embedder = None


def get_embedder() -> HuggingFaceEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = HuggingFaceEmbedding(model_name=config.EMBED_MODEL)
    return _embedder
