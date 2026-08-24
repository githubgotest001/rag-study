"""FastAPI 应用入口。

启动方式（在 backend/ 目录下）：
    uvicorn app.main:app --reload --port 8000

- 启动时若知识库为空，自动导入 samples/ 下的示例文档（可用 SEED_ON_STARTUP=false 关闭）；
- 开发模式下前端由 Vite 提供并通过 proxy 转发 /api；
- 若存在 frontend/dist（已执行 npm run build），后端会直接托管这些静态文件，
  实现单端口部署（生产模式）。
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .config import REPO_DIR, Settings, get_settings
from .rag.pipeline import RAGService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """应用工厂：测试时可以传入自定义 Settings（指向临时目录）。"""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        service = RAGService(settings)
        app.state.rag_service = service
        if settings.seed_on_startup:
            imported = service.seed_samples()
            if imported:
                logger.info("已自动导入 %d 篇示例文档：%s", len(imported), "、".join(imported))
        yield

    app = FastAPI(
        title="RAG 学习系统",
        description="一个教学向的检索增强生成（RAG）完整示例：文档入库 → 切块 → 向量化 → 检索 → 生成答案 → 引用来源",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 开发时前后端分端口运行，放开 CORS 方便学习调试
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    # 生产模式：托管前端构建产物（若存在）
    dist_dir = Path(REPO_DIR / "frontend" / "dist")
    if dist_dir.is_dir():
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")
        logger.info("检测到 frontend/dist，已由后端托管前端静态资源")

    return app


app = create_app()
