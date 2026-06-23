import hashlib
import json
from pathlib import Path

from llama_index.core import VectorStoreIndex, StorageContext, Document
from llama_index.core.node_parser import SentenceSplitter

from src.core import config, db
from src.core.embedder import get_embedder
from src.core.logger import get_logger
from src.core.vector_store import get_vector_store

log = get_logger("ingest")


def _doc_id(filepath: str) -> str:
    return hashlib.md5(filepath.encode()).hexdigest()


def ingest_file(filepath: str, module: str = "general") -> bool:
    doc_id = _doc_id(filepath)
    if db.is_doc_indexed(doc_id):
        log.debug(f"skipped {Path(filepath).name} (already indexed)")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    content = data.get("content", "")
    if not content:
        log.warning(f"skipped {Path(filepath).name} (no content field)")
        return False

    title = data.get("title", Path(filepath).stem)
    tags = data.get("tags", [])

    metadata = {
        "title": title,
        "tags": json.dumps(tags),
        "source": data.get("source", ""),
        "date": data.get("date", ""),
        "module": module,
        "doc_id": doc_id,
    }

    document = Document(text=content, metadata=metadata, id_=doc_id)
    splitter = SentenceSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)
    nodes = splitter.get_nodes_from_documents([document])

    vector_store = get_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    VectorStoreIndex(nodes, storage_context=storage_context, embed_model=get_embedder())

    db.upsert_knowledge_doc(module, doc_id, filepath, title, tags)
    log.info(f"indexed {Path(filepath).name} — title='{title}' chunks={len(nodes)}")
    return True


def ingest_directory(directory: str = None, module: str = "general") -> dict:
    directory = directory or config.RAW_DATA_PATH
    results = {"indexed": 0, "skipped": 0, "errors": []}
    log.info(f"ingest_directory: scanning {directory}")

    for filepath in Path(directory).rglob("*.json"):
        try:
            if ingest_file(str(filepath), module):
                results["indexed"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            log.error(f"error indexing {filepath.name}: {e}", exc_info=True)
            results["errors"].append(f"{filepath.name}: {e}")

    log.info(f"ingest done — indexed={results['indexed']} skipped={results['skipped']} errors={len(results['errors'])}")
    return results
