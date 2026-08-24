"""步骤 6 & 7：提示词增强（Augment）与生成（Generate）。

- Augment：把检索到的文本块按固定模板拼进提示词（prompt），
  让 LLM「只根据给定资料回答」，这是 RAG 抑制幻觉的关键；
- Generate：两条路线
  1. 配置了 OPENAI_API_KEY 时，调用 OpenAI 兼容接口做真正的 LLM 生成；
  2. 没有 Key（或调用失败）时，降级为“抽取式回答”：
     把检索片段再拆成句子，挑出与问题最相似的几句拼接成答案。
     这样即使完全离线，学习者也能看到完整的 RAG 链路。
"""

import logging
import re

from ..config import Settings
from .embedding import Embedder
from .vectorstore import RetrievedChunk

logger = logging.getLogger(__name__)

# 提示词模板：明确要求“只根据资料回答 + 标注引用编号”
PROMPT_TEMPLATE = """你是一个严谨的知识库问答助手。请只根据下面提供的资料回答用户的问题：
- 如果资料中没有相关信息，请直接说“根据现有资料无法回答这个问题”；
- 回答时在相应句子末尾用 [编号] 标注引用了哪条资料；
- 用简体中文回答，简洁准确。

【资料】
{context}

【问题】
{question}

【回答】"""


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    """Augment：把检索到的块按编号拼成上下文，填进提示词模板。"""
    context = "\n\n".join(
        f"[{i + 1}] 来源《{chunk.source}》第 {chunk.chunk_index + 1} 块：\n{chunk.text}"
        for i, chunk in enumerate(chunks)
    )
    return PROMPT_TEMPLATE.format(context=context, question=question)


def generate_with_llm(prompt: str, settings: Settings) -> str:
    """调用 OpenAI 兼容接口生成答案（支持自定义 base_url，可接各类兼容服务）。"""
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
    )
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return (response.choices[0].message.content or "").strip()


_SENTENCE_RE = re.compile(r"(?<=[。！？!?；;])")


def extractive_answer(
    question: str,
    chunks: list[RetrievedChunk],
    embedder: Embedder,
    max_sentences: int = 4,
) -> str:
    """抽取式回答（无 LLM 的 fallback）。

    做法：把检索到的块拆成句子，对每个句子再算一次与问题的相似度，
    挑出最相关的几句，按相关度排序拼成回答，并标注每句来自哪条引用。
    """
    # 收集候选句子：(句子文本, 引用编号)
    candidates: list[tuple[str, int]] = []
    seen: set[str] = set()
    for i, chunk in enumerate(chunks):
        for sentence in _SENTENCE_RE.split(chunk.text.replace("\n", " ")):
            sentence = sentence.strip()
            if len(sentence) >= 8 and sentence not in seen:
                seen.add(sentence)
                candidates.append((sentence, i + 1))

    if not candidates:
        return "抱歉，检索到的内容太少，无法组织出回答。请尝试换个问法或上传更多文档。"

    # 句子级重排：与问题向量做点积（向量已归一化，点积即余弦相似度）
    query_vec = embedder.embed_query(question)
    sentence_vecs = embedder.embed_texts([s for s, _ in candidates])
    scored = [
        (sum(q * v for q, v in zip(query_vec, vec)), sentence, ref)
        for vec, (sentence, ref) in zip(sentence_vecs, candidates)
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:max_sentences]

    lines = [f"- {sentence} [{ref}]" for _, sentence, ref in top]
    return (
        "根据知识库中最相关的内容，整理出以下要点（句末 [编号] 对应下方引用来源）：\n\n"
        + "\n".join(lines)
    )


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    settings: Settings,
    embedder: Embedder,
) -> tuple[str, str, str | None, str]:
    """生成最终答案。

    返回：(答案, 生成方式 "llm"/"extractive", 使用的模型名, 增强后的完整 prompt)
    """
    prompt = build_prompt(question, chunks)

    if settings.llm_available:
        try:
            answer = generate_with_llm(prompt, settings)
            if answer:
                return answer, "llm", settings.openai_model, prompt
            logger.warning("LLM 返回了空回答，降级为抽取式回答")
        except Exception as exc:
            logger.warning("LLM 调用失败（%s），降级为抽取式回答", exc)

    answer = extractive_answer(question, chunks, embedder)
    return answer, "extractive", None, prompt
