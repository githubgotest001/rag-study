// 与后端 backend/app/schemas.py 对应的类型定义

export interface DocumentInfo {
  id: string
  filename: string
  size_bytes: number
  num_chunks: number
  num_chars: number
  origin: 'upload' | 'sample'
  created_at: string
  chunk_size: number
  chunk_overlap: number
}

export interface IngestTimings {
  ingest_ms: number
  chunk_ms: number
  embed_ms: number
  index_ms: number
}

export interface UploadResponse {
  document: DocumentInfo
  timings: IngestTimings
}

export interface ChunkInfo {
  chunk_id: string
  chunk_index: number
  text: string
  num_chars: number
}

export interface ChunksResponse {
  document: DocumentInfo
  chunks: ChunkInfo[]
}

export interface Citation {
  ref: number
  doc_id: string
  source: string
  chunk_index: number
  text: string
  score: number
}

export interface QueryResponse {
  answer: string
  mode: 'llm' | 'extractive' | 'empty'
  model: string | null
  citations: Citation[]
  prompt: string | null
  timings: Record<string, number>
}

export interface SettingsInfo {
  chunk_size: number
  chunk_overlap: number
  top_k: number
  embedding_model: string
  llm_enabled: boolean
  llm_active: boolean
  openai_model: string
  openai_base_url: string | null
  openai_api_key_set: boolean
}

export interface HealthInfo {
  status: 'ok'
  num_documents: number
  num_chunks: number
  embedding_model_loaded: boolean
}
