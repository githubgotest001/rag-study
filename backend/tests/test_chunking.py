"""切块逻辑的边界测试（纯函数，不需要加载模型）。"""

import pytest

from app.rag.chunking import chunk_text


def test_empty_text_returns_empty_list():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_returns_single_chunk():
    text = "RAG 是检索增强生成。"
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
    assert chunks == [text]


def test_chunk_length_never_exceeds_size_plus_overlap():
    # 构造带中文标点的长文本
    text = "检索增强生成是一种结合检索与生成的技术。" * 100
    chunk_size, chunk_overlap = 120, 30
    chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    assert len(chunks) > 1
    assert all(len(c) <= chunk_size + chunk_overlap for c in chunks)


def test_overlap_between_consecutive_chunks():
    # 无标点的连续文本会被硬切，便于精确验证重叠行为
    text = "a" * 1000
    chunk_size, chunk_overlap = 100, 20
    chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    assert len(chunks) > 1
    for prev, curr in zip(chunks, chunks[1:]):
        # 每个后续块都以上一块结尾的 chunk_overlap 个字符开头
        assert curr.startswith(prev[-chunk_overlap:])


def test_zero_overlap_is_allowed():
    text = "b" * 500
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=0)
    assert len(chunks) == 5
    assert all(len(c) == 100 for c in chunks)


def test_no_content_lost_when_no_overlap():
    text = "c" * 457
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=0)
    assert "".join(chunks) == text


def test_long_sentence_is_hard_split():
    # 单个"句子"超过 chunk_size 时按固定长度硬切，不会产生超长块
    text = "d" * 350
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
    assert all(len(c) <= 110 for c in chunks)


def test_invalid_params_raise_value_error():
    with pytest.raises(ValueError):
        chunk_text("文本", chunk_size=0, chunk_overlap=0)
    with pytest.raises(ValueError):
        chunk_text("文本", chunk_size=100, chunk_overlap=100)  # overlap >= size
    with pytest.raises(ValueError):
        chunk_text("文本", chunk_size=100, chunk_overlap=-1)
