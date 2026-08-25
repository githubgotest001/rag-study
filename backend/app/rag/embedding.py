"""步骤 3：向量化（Embed）—— 把文本变成语义向量。

使用 sentence-transformers（默认模型 all-MiniLM-L6-v2，384 维，CPU 可跑）。
两段语义相近的文本，其向量的余弦相似度会更高——这就是“语义检索”的基础。

说明：
- 模型懒加载：第一次调用时才加载（首次运行会自动从 HuggingFace 下载，约 90MB）；
- normalize_embeddings=True 会把向量归一化为单位长度，
  这样余弦相似度可以直接用点积计算，Chroma 的 cosine 距离也更好解释。
"""

import logging
import threading

logger = logging.getLogger(__name__)


class Embedder:
    """sentence-transformers 的轻量封装（线程安全的懒加载单例模式）。"""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    # 延迟导入：让不需要向量化的代码路径（如纯切块测试）不必加载 torch
                    from sentence_transformers import SentenceTransformer

                    logger.info("正在加载 embedding 模型 %s（首次运行会自动下载）...", self.model_name)
                    self._model = SentenceTransformer(self.model_name, device="cpu")
                    logger.info("embedding 模型加载完成")
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文档块。"""
        if not texts:
            return []
        model = self._get_model()
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        """向量化用户问题（与文档块用同一个模型，保证在同一向量空间）。"""
        return self.embed_texts([query])[0]
