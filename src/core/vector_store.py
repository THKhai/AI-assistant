from src.core import config


def get_vector_store(collection: str = None):
    collection = collection or config.COLLECTION_NAME

    if config.VECTOR_BACKEND == "chroma":
        import chromadb
        from llama_index.vector_stores.chroma import ChromaVectorStore
        client = chromadb.PersistentClient(path=config.CHROMA_PATH)
        chroma_col = client.get_or_create_collection(collection)
        return ChromaVectorStore(chroma_collection=chroma_col)

    elif config.VECTOR_BACKEND == "qdrant":
        from qdrant_client import QdrantClient
        from llama_index.vector_stores.qdrant import QdrantVectorStore
        client = QdrantClient(url=config.QDRANT_URL)
        return QdrantVectorStore(client=client, collection_name=collection)

    raise ValueError(f"Unknown VECTOR_BACKEND: {config.VECTOR_BACKEND}")
