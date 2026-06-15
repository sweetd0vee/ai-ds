import asyncio

from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import LLMChain

from ..config import settings

_llm_analyst_cache: dict[str, Ollama] = {}


def get_llm_analyst(model: str | None = None, *, num_predict: int = 1200) -> Ollama:
    name = (model or settings.analyst_model).strip()
    cache_key = f"{name}:{num_predict}"
    if cache_key not in _llm_analyst_cache:
        _llm_analyst_cache[cache_key] = Ollama(
            model=name,
            base_url=settings.ollama_base_url,
            temperature=0.4,
            num_predict=num_predict,
            num_ctx=8192,
        )
    return _llm_analyst_cache[cache_key]


async def chain_invoke(
    prompt_template: str,
    output_key: str,
    llm,
    inputs: dict | None = None,
    partial: dict | None = None,
) -> str:
    prompt = PromptTemplate.from_template(prompt_template)
    if partial:
        for key, value in partial.items():
            prompt = prompt.partial(**{key: value})
    chain = LLMChain(llm=llm, prompt=prompt, output_key=output_key)
    result = await asyncio.to_thread(chain.invoke, inputs or {})
    return str(result.get(output_key, "") or "")
