"""运行配置（RAG 学习系统）。

所有配置都可以通过环境变量或 backend/.env 覆盖，
例如 CHUNK_SIZE=500、OPENAI_API_KEY=sk-xxx。
参考 backend/.env.example。
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录（config.py 位于 backend/app/ 下）
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- 路径 ----------
    # 运行时数据目录：向量库、文档注册表都放在这里（已在 .gitignore 中忽略）
    data_dir: Path = BACKEND_DIR / "data"
    # 示例文档目录：首次启动时自动入库
    samples_dir: Path = REPO_DIR / "samples"

    # ---------- 切块（Chunk）----------
    # chunk_size：每个文本块的最大字符数；chunk_overlap：相邻块之间的重叠字符数
    chunk_size: int = 400
    chunk_overlap: int = 80

    # ---------- 检索（Retrieve）----------
    # 每次查询返回的最相似文本块数量
    top_k: int = 4

    # ---------- 向量化（Embed）----------
    # sentence-transformers 模型名，默认 all-MiniLM-L6-v2（CPU 可跑，首次会自动下载）
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ---------- 生成（Generate）----------
    # 是否启用 LLM 生成；即使为 True，没有 OPENAI_API_KEY 时也会自动降级为“检索拼接回答”
    llm_enabled: bool = True
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"

    # ---------- 其它 ----------
    # 首次启动（知识库为空）时是否自动导入 samples/ 下的示例文档
    seed_on_startup: bool = True
    # 单个上传文件的大小上限（字节）
    max_upload_bytes: int = 10 * 1024 * 1024

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def registry_path(self) -> Path:
        return self.data_dir / "documents.json"

    @property
    def llm_available(self) -> bool:
        """只有同时满足“开启开关 + 配置了 API Key”才会真正调用 LLM。"""
        return self.llm_enabled and bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
