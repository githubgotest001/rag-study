"""API 请求/响应模型（Pydantic）。

所有接口的输入输出都有明确的类型和校验，
校验失败时 FastAPI 会返回 422 与具体的错误字段，方便学习者排查。
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DocumentInfo(BaseModel):
    """知识库中一个文档的元信息。"""

    id: str
    filename: str
    size_bytes: int
    num_chunks: int
    num_chars: int
    origin: Literal["upload", "sample"]
    created_at: str
    chunk_size: int
    chunk_overlap: int


class IngestTimings(BaseModel):
    """入库各步骤耗时（毫秒），用于前端可视化 Ingest→Chunk→Embed→Index。"""

    ingest_ms: float
    chunk_ms: float
    embed_ms: float
    index_ms: float


class UploadResponse(BaseModel):
    document: DocumentInfo
    timings: IngestTimings


class ChunkInfo(BaseModel):
    """一个文本块（切块预览用）。"""

    chunk_id: str
    chunk_index: int
    text: str
    num_chars: int


class ChunksResponse(BaseModel):
    document: DocumentInfo
    chunks: list[ChunkInfo]


class QueryRequest(BaseModel):
    """问答请求。"""

    question: str = Field(description="用户的问题")
    top_k: int | None = Field(
        default=None, ge=1, le=20, description="检索返回的块数（默认用服务端配置）"
    )

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("问题不能为空，请输入你想了解的内容")
        if len(value) > 1000:
            raise ValueError("问题太长了（最多 1000 字），请精简后再试")
        return value


class Citation(BaseModel):
    """答案的一条引用来源。"""

    ref: int = Field(description="引用编号，与答案中的 [n] 对应")
    doc_id: str
    source: str = Field(description="来源文件名")
    chunk_index: int
    text: str = Field(description="命中的文本块内容")
    score: float = Field(description="相似度分数（0~1，越大越相关）")


class QueryResponse(BaseModel):
    """问答响应：答案 + 引用 + 教学信息（prompt、各步骤耗时）。"""

    answer: str
    mode: Literal["llm", "extractive", "empty"] = Field(
        description="生成方式：llm=大模型生成；extractive=检索片段拼接（无 LLM 时的降级方案）；empty=知识库为空"
    )
    model: str | None = Field(description="使用的 LLM 模型名（extractive 模式为 null）")
    citations: list[Citation]
    prompt: str | None = Field(description="增强后的完整提示词（教学展示用）")
    timings: dict[str, float] = Field(description="各步骤耗时（毫秒）")


class SettingsResponse(BaseModel):
    """当前运行配置（不包含任何密钥）。"""

    chunk_size: int
    chunk_overlap: int
    top_k: int
    embedding_model: str
    llm_enabled: bool = Field(description="LLM 开关（配置项）")
    llm_active: bool = Field(description="LLM 是否真正可用（开关开启且已配置 API Key）")
    openai_model: str
    openai_base_url: str | None
    openai_api_key_set: bool = Field(description="是否配置了 API Key（不返回 Key 本身）")


class HealthResponse(BaseModel):
    status: Literal["ok"]
    num_documents: int
    num_chunks: int
    embedding_model_loaded: bool


class DeleteResponse(BaseModel):
    ok: bool
    id: str
