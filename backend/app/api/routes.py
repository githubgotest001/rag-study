"""REST API 路由。

接口一览：
- POST   /api/documents              上传文档（走完 Ingest→Chunk→Embed→Index）
- GET    /api/documents              文档列表
- DELETE /api/documents/{doc_id}     删除文档（同时删除向量库中的块）
- GET    /api/documents/{doc_id}/chunks  查看切块结果
- POST   /api/query                  问答（Embed→Retrieve→Augment→Generate）
- GET    /api/health                 健康检查
- GET    /api/settings               当前运行配置（不泄露密钥）
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile

from .. import schemas
from ..rag.loading import EmptyDocumentError, UnsupportedFileError
from ..rag.pipeline import DocumentNotFoundError, RAGService

router = APIRouter(prefix="/api", tags=["rag"])


def get_service(request: Request) -> RAGService:
    return request.app.state.rag_service


@router.post("/documents", response_model=schemas.UploadResponse, status_code=201)
async def upload_document(request: Request, file: UploadFile) -> schemas.UploadResponse:
    """上传一个文档并完成入库（解析 → 切块 → 向量化 → 建索引）。"""
    service = get_service(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="没有收到文件名，请重新选择文件")

    data = await file.read()
    if len(data) > service.settings.max_upload_bytes:
        limit_mb = service.settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"文件太大，最大支持 {limit_mb}MB")
    if not data:
        raise HTTPException(status_code=400, detail="文件内容为空，请检查后重新上传")

    try:
        doc, timings = service.ingest_file(file.filename, data, origin="upload")
    except (UnsupportedFileError, EmptyDocumentError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return schemas.UploadResponse(document=schemas.DocumentInfo(**doc), timings=schemas.IngestTimings(**timings))


@router.get("/documents", response_model=list[schemas.DocumentInfo])
def list_documents(request: Request) -> list[schemas.DocumentInfo]:
    """列出知识库中的所有文档。"""
    service = get_service(request)
    return [schemas.DocumentInfo(**doc) for doc in service.list_documents()]


@router.delete("/documents/{doc_id}", response_model=schemas.DeleteResponse)
def delete_document(request: Request, doc_id: str) -> schemas.DeleteResponse:
    """删除文档及其在向量库中的所有块。"""
    service = get_service(request)
    try:
        service.delete_document(doc_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在，可能已被删除") from exc
    return schemas.DeleteResponse(ok=True, id=doc_id)


@router.get("/documents/{doc_id}/chunks", response_model=schemas.ChunksResponse)
def get_document_chunks(request: Request, doc_id: str) -> schemas.ChunksResponse:
    """查看一个文档的切块结果（教学：直观看到 chunk_size / overlap 的效果）。"""
    service = get_service(request)
    try:
        doc = service.get_document(doc_id)
        chunks = service.get_chunks(doc_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在，可能已被删除") from exc
    return schemas.ChunksResponse(
        document=schemas.DocumentInfo(**doc),
        chunks=[schemas.ChunkInfo(**chunk) for chunk in chunks],
    )


@router.post("/query", response_model=schemas.QueryResponse)
def query(request: Request, body: schemas.QueryRequest) -> schemas.QueryResponse:
    """RAG 问答：检索相关块并生成带引用的答案。"""
    service = get_service(request)
    result = service.query(body.question, top_k=body.top_k)
    return schemas.QueryResponse(**result)


@router.get("/health", response_model=schemas.HealthResponse)
def health(request: Request) -> schemas.HealthResponse:
    """健康检查：返回文档数、块数、模型加载状态。"""
    service = get_service(request)
    return schemas.HealthResponse(
        status="ok",
        num_documents=len(service.list_documents()),
        num_chunks=service.store.count(),
        embedding_model_loaded=service.embedder.is_loaded,
    )


@router.get("/settings", response_model=schemas.SettingsResponse)
def get_settings_info(request: Request) -> schemas.SettingsResponse:
    """当前运行配置（只读展示；绝不返回 API Key 本身）。"""
    s = get_service(request).settings
    return schemas.SettingsResponse(
        chunk_size=s.chunk_size,
        chunk_overlap=s.chunk_overlap,
        top_k=s.top_k,
        embedding_model=s.embedding_model,
        llm_enabled=s.llm_enabled,
        llm_active=s.llm_available,
        openai_model=s.openai_model,
        openai_base_url=s.openai_base_url,
        openai_api_key_set=bool(s.openai_api_key),
    )
