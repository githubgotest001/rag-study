"""步骤 4 & 5：索引（Index）与检索（Retrieve）—— ChromaDB 向量库封装。

- Index：把「文本块 + 向量 + 元数据」写入 Chroma 集合，持久化到本地目录；
- Retrieve：把问题向量传给 Chroma，用 HNSW 近似最近邻算法找出最相似的 top_k 个块。

我们把集合的距离度量设为 cosine（余弦距离），
相似度分数 = 1 - 余弦距离，范围约在 0~1，越大越相关。
"""

from pathlib import Path
from typing import Any

import chromadb

COLLECTION_NAME = "rag_study"


class RetrievedChunk:
    """一次检索命中的文本块（含相似度分数与来源信息）。"""

    def __init__(self, chunk_id: str, text: str, score: float, metadata: dict[str, Any]):
        self.chunk_id = chunk_id
        self.text = text
        self.score = score
        self.doc_id = str(metadata.get("doc_id", ""))
        self.source = str(metadata.get("source", ""))
        self.chunk_index = int(metadata.get("chunk_index", 0))


class VectorStore:
    """ChromaDB 持久化向量库封装。"""

    def __init__(self, persist_dir: Path) -> None:
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  # 用余弦距离衡量语义相似度
        )

    def count(self) -> int:
        return self._collection.count()

    def add_chunks(
        self,
        doc_id: str,
        source: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        """把一个文档的所有块写入索引。

        每个块记录三类信息：
        - id：全局唯一（doc_id + 块序号）
        - embedding：语义向量（检索时用它算相似度）
        - metadata：来源文件、块序号（回答时用于展示引用）
        """
        if not chunks:
            return
        self._collection.add(
            ids=[f"{doc_id}:{i}" for i in range(len(chunks))],
            embeddings=embeddings,
            documents=chunks,
            metadatas=[
                {"doc_id": doc_id, "source": source, "chunk_index": i}
                for i in range(len(chunks))
            ],
        )

    def delete_document(self, doc_id: str) -> None:
        """删除某个文档的全部块。"""
        self._collection.delete(where={"doc_id": doc_id})

    def get_document_chunks(self, doc_id: str) -> list[dict[str, Any]]:
        """取出某个文档的全部块（按块序号排序），用于前端“切块预览”。"""
        result = self._collection.get(where={"doc_id": doc_id})
        items = [
            {
                "chunk_id": chunk_id,
                "text": text,
                "chunk_index": int(meta.get("chunk_index", 0)),
                "num_chars": len(text),
            }
            for chunk_id, text, meta in zip(
                result["ids"], result["documents"] or [], result["metadatas"] or []
            )
        ]
        items.sort(key=lambda item: item["chunk_index"])
        return items

    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        """用问题向量做近似最近邻检索，返回最相似的 top_k 个块。"""
        total = self.count()
        if total == 0:
            return []
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, total),
            include=["documents", "metadatas", "distances"],
        )
        hits: list[RetrievedChunk] = []
        for chunk_id, text, meta, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            # cosine 距离 -> 相似度分数（越大越相关，约在 0~1 之间）
            score = max(0.0, min(1.0, 1.0 - float(distance)))
            hits.append(RetrievedChunk(chunk_id, text, score, meta))
        return hits
