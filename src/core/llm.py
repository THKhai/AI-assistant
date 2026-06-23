from llama_index.llms.openai_like import OpenAILike
from src.core import config
from src.core.logger import get_logger

log = get_logger("llm")
_llm = None


def get_llm() -> OpenAILike:
    global _llm
    if _llm is None:
        _llm = OpenAILike(
            model=config.DEEPSEEK_MODEL,
            api_base=config.DEEPSEEK_BASE_URL,
            api_key=config.DEEPSEEK_API_KEY,
            is_chat_model=True,
            context_window=65536,
        )
        log.info(f"LLM initialized — model={config.DEEPSEEK_MODEL} base={config.DEEPSEEK_BASE_URL}")
    return _llm
