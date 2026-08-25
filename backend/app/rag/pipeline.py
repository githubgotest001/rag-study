"""RAG 流水线编排：把 7 个步骤串起来的核心服务。

入库链路：Ingest（loading.py）→ Chunk（chunking.py）→ Embed（embedding.py）→ Index（vectorstore.py）
问答链路：Embed 问题 → Retrieve（vectorstore.py）→ Augment + Generate（generation.py）

另外维护一个 JSON 文档注册表（data/documents.json），
记录每个文档的元信息（文件名、块数、上传时间等），供前端列表展示。
"""

import json
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ..config import Settings
from . import chunking, generation, loading
from .embedding import Embedder
from .vectorstore import RetrievedChunk, VectorStore


class DocumentNotFoundError(KeyError):
    """文档不存在。"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RAGService:
    """RAG 学习系统的核心服务：文档管理 + 问答。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.embedder = Embedder(settings.embedding_model)
        self.store = VectorStore(settings.chroma_dir)
        self._registry_lock = threading.Lock()

    # ---------- 文档注册表（JSON 文件） ----------

    def _load_registry(self) -> list[dict[str, Any]]:
        path = self.settings.registry_path
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_registry(self, docs: list[dict[str, Any]]) -> None:
        self.settings.registry_path.write_text(
            json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ---------- 入库链路：Ingest → Chunk → Embed → Index ----------

    def ingest_file(
        self, filename: str, data: bytes, origin: str = "upload"
    ) -> tuple[dict[str, Any], dict[str, float]]:
        """完整的文档入库流程，返回 (文档信息, 各步骤耗时毫秒)。"""
        timings: dict[str, float] = {}

        # 步骤 1 Ingest：解析文件为纯文本
        t0 = time.perf_counter()
        text = loading.extract_text(filename, data)
        timings["ingest_ms"] = (time.perf_counter() - t0) * 1000

        # 步骤 2 Chunk：切块
        t0 = time.perf_counter()
        chunks = chunking.chunk_text(
            text,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        timings["chunk_ms"] = (time.perf_counter() - t0) * 1000
        if not chunks:
            raise loading.EmptyDocumentError("切块后没有得到任何内容，请检查文件")

        # 步骤 3 Embed：向量化所有块
        t0 = time.perf_counter()
        embeddings = self.embedder.embed_texts(chunks)
        timings["embed_ms"] = (time.perf_counter() - t0) * 1000

        # 步骤 4 Index：写入 Chroma 向量库
        doc_id = uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        self.store.add_chunks(doc_id, filename, chunks, embeddings)
        timings["index_ms"] = (time.perf_counter() - t0) * 1000

        doc = {
            "id": doc_id,
            "filename": filename,
            "size_bytes": len(data),
            "num_chunks": len(chunks),
            "num_chars": len(text),
            "origin": origin,
            "created_at": _now_iso(),
            "chunk_size": self.settings.chunk_size,
            "chunk_overlap": self.settings.chunk_overlap,
        }
        with self._registry_lock:
            docs = self._load_registry()
            docs.append(doc)
            self._save_registry(docs)
        return doc, timings

    # ---------- 文档管理 ----------

    def list_documents(self) -> list[dict[str, Any]]:
        docs = self._load_registry()
        docs.sort(key=lambda d: d["created_at"], reverse=True)
        return docs

    def get_document(self, doc_id: str) -> dict[str, Any]:
        for doc in self._load_registry():
            if doc["id"] == doc_id:
                return doc
        raise DocumentNotFoundError(doc_id)

    def delete_document(self, doc_id: str) -> None:
        with self._registry_lock:
            docs = self._load_registry()
            remaining = [d for d in docs if d["id"] != doc_id]
            if len(remaining) == len(docs):
                raise DocumentNotFoundError(doc_id)
            self.store.delete_document(doc_id)
            self._save_registry(remaining)

    def get_chunks(self, doc_id: str) -> list[dict[str, Any]]:
        self.get_document(doc_id)  # 不存在时抛 DocumentNotFoundError
        return self.store.get_document_chunks(doc_id)

    # ---------- 问答链路：Embed 问题 → Retrieve → Augment → Generate ----------

    def query(self, question: str, top_k: int | None = None) -> dict[str, Any]:
        """回答一个问题，返回答案、引用、各步骤耗时等完整信息。"""
        timings: dict[str, float] = {}
        top_k = top_k or self.settings.top_k

        if self.store.count() == 0:
            return {
                "answer": "知识库目前是空的，请先在「知识库」页面上传文档，再来提问。",
                "mode": "empty",
                "model": None,
                "citations": [],
                "prompt": None,
                "timings": timings,
            }

        # 步骤 3（对问题）Embed：问题必须用与文档相同的模型向量化
        t0 = time.perf_counter()
        query_vec = self.embedder.embed_query(question)
        timings["embed_ms"] = (time.perf_counter() - t0) * 1000

        # 步骤 5 Retrieve：在向量库中找最相似的 top_k 个块
        t0 = time.perf_counter()
        hits: list[RetrievedChunk] = self.store.query(query_vec, top_k)
        timings["retrieve_ms"] = (time.perf_counter() - t0) * 1000

        # 步骤 6 + 7 Augment & Generate：拼提示词并生成答案
        t0 = time.perf_counter()
        answer, mode, model, prompt = generation.generate_answer(
            question, hits, self.settings, self.embedder
        )
        timings["generate_ms"] = (time.perf_counter() - t0) * 1000

        return {
            "answer": answer,
            "mode": mode,
            "model": model,
            "citations": [
                {
                    "ref": i + 1,
                    "doc_id": hit.doc_id,
                    "source": hit.source,
                    "chunk_index": hit.chunk_index,
                    "text": hit.text,
                    "score": round(hit.score, 4),
                }
                for i, hit in enumerate(hits)
            ],
            "prompt": prompt,
            "timings": {k: round(v, 1) for k, v in timings.items()},
        }

    # ---------- 示例文档 seed ----------

    def seed_samples(self, force: bool = False) -> list[str]:
        """把 samples/ 目录下的示例文档导入知识库。

        默认只在知识库为空时执行（避免重启后重复导入）；force=True 时强制导入。
        返回本次导入的文件名列表。
        """
        samples_dir = self.settings.samples_dir
        if not samples_dir.is_dir():
            return []
        if not force and self.list_documents():
            return []
        imported: list[str] = []
        for path in sorted(samples_dir.iterdir()):
            if path.suffix.lower() in loading.SUPPORTED_EXTENSIONS:
                self.ingest_file(path.name, path.read_bytes(), origin="sample")
                imported.append(path.name)
        return imported
