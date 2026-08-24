"""pytest 公共 fixture。

client fixture 是 session 级别的：整个测试会话只加载一次 embedding 模型、
只建一个临时向量库（启动时自动导入 samples/ 示例文档），加快测试速度。
"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import REPO_DIR, Settings
from app.main import create_app


@pytest.fixture(scope="session")
def client():
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(
            data_dir=Path(tmp) / "data",
            samples_dir=REPO_DIR / "samples",
            seed_on_startup=True,
            # 测试不走 LLM，固定验证抽取式回答链路
            llm_enabled=False,
            openai_api_key=None,
        )
        app = create_app(settings)
        # 用 with 触发 lifespan（初始化服务 + 自动 seed 示例文档）
        with TestClient(app) as test_client:
            yield test_client
