"""步骤 2：切块（Chunk）。

为什么要切块？
- Embedding 模型和 LLM 的上下文长度有限，整篇文档无法直接向量化；
- 切成小块后，每个块的语义更聚焦，检索命中率更高；
- chunk_overlap（重叠）让相邻块共享一小段文本，避免关键句子被“拦腰截断”。

本实现是“句子感知”的滑动窗口切块：
1. 先按中英文标点/换行把文本拆成句子（超长句子再按 chunk_size 硬切）；
2. 贪心地把句子装进块里，装满 chunk_size 就产出一个块；
3. 新块以上一个块结尾的 chunk_overlap 个字符开头，形成重叠。

不变量（测试覆盖）：
- 空文本 -> 空列表；
- 每个块长度 <= chunk_size + chunk_overlap；
- 当 chunk_overlap > 0 时，第 i+1 个块以第 i 个块的结尾开头。
"""

import re

# 句子结束符：中文/英文标点 + 换行（保留分隔符在句子末尾）
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？；!?;\n])")


def _normalize(text: str) -> str:
    """统一换行符，压缩连续空行，去掉首尾空白。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    """按标点/换行拆句，保留分隔符，过滤空串。"""
    return [s for s in _SENTENCE_SPLIT_RE.split(text) if s]


def chunk_text(text: str, chunk_size: int = 400, chunk_overlap: int = 80) -> list[str]:
    """把长文本切成带重叠的小块。

    参数：
        text: 原始文本
        chunk_size: 块的目标最大字符数（必须 > 0）
        chunk_overlap: 相邻块的重叠字符数（必须满足 0 <= overlap < size）
    返回：
        文本块列表（已去掉首尾空白的非空字符串）
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须满足 0 <= chunk_overlap < chunk_size")

    text = _normalize(text)
    if not text:
        return []

    # 第一步：拆句；超过 chunk_size 的超长句子按固定长度硬切
    pieces: list[str] = []
    for sentence in split_sentences(text):
        if len(sentence) <= chunk_size:
            pieces.append(sentence)
        else:
            pieces.extend(
                sentence[i : i + chunk_size] for i in range(0, len(sentence), chunk_size)
            )

    # 第二步：贪心装箱 + 字符级重叠
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) > chunk_size:
            chunks.append(current)
            # 新块以上一块的结尾 chunk_overlap 个字符开头（形成重叠）
            current = current[-chunk_overlap:] if chunk_overlap > 0 else ""
        current += piece
    if current:
        chunks.append(current)

    return [c.strip() for c in chunks if c.strip()]
