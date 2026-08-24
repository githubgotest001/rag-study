"""步骤 1：文档入库（Ingest）—— 把不同格式的文件解析成纯文本。

支持格式：
- .txt / .md / .markdown：按 UTF-8 读取（失败时尝试 GBK，兼容中文 Windows 文件）
- .pdf：用 pypdf 逐页抽取文本

解析失败时抛出 UnsupportedFileError / EmptyDocumentError，
API 层会把它们翻译成对学习者友好的中文错误信息。
"""

import io
from pathlib import Path

SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf"}


class UnsupportedFileError(ValueError):
    """文件格式不支持。"""


class EmptyDocumentError(ValueError):
    """解析后没有得到任何文本。"""


def _decode_text(data: bytes) -> str:
    """优先 UTF-8，失败再试 GBK，最后宽松解码兜底。"""
    for encoding in ("utf-8", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # pypdf 对损坏文件会抛各种异常
        raise UnsupportedFileError(f"PDF 解析失败：{exc}") from exc
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def extract_text(filename: str, data: bytes) -> str:
    """根据文件扩展名解析出纯文本。

    参数：
        filename: 原始文件名（用于判断格式）
        data: 文件的二进制内容
    返回：
        解析出的纯文本
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = "、".join(sorted(SUPPORTED_EXTENSIONS))
        raise UnsupportedFileError(
            f"暂不支持 {suffix or '无扩展名'} 格式，请上传以下格式之一：{supported}"
        )

    text = _extract_pdf(data) if suffix == ".pdf" else _decode_text(data)

    if not text.strip():
        raise EmptyDocumentError(
            "文件解析成功但没有提取到任何文本（可能是扫描版 PDF 或空文件）"
        )
    return text
