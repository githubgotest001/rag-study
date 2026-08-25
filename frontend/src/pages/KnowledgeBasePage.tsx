import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import PipelineSteps from '../components/PipelineSteps'
import type { ChunksResponse, DocumentInfo, UploadResponse } from '../types'
import { formatBytes, formatDate, formatMs } from '../utils'

export default function KnowledgeBasePage() {
  const [docs, setDocs] = useState<DocumentInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpload, setLastUpload] = useState<UploadResponse | null>(null)
  const [preview, setPreview] = useState<ChunksResponse | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function refresh() {
    try {
      setDocs(await api.listDocuments())
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  async function handleUpload(file: File) {
    setUploading(true)
    setError(null)
    setLastUpload(null)
    try {
      const resp = await api.uploadDocument(file)
      setLastUpload(resp)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : '上传失败')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleDelete(doc: DocumentInfo) {
    if (!window.confirm(`确定删除「${doc.filename}」吗？其向量库中的 ${doc.num_chunks} 个块也会被删除。`)) {
      return
    }
    setDeletingId(doc.id)
    setError(null)
    try {
      await api.deleteDocument(doc.id)
      if (preview?.document.id === doc.id) setPreview(null)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除失败')
    } finally {
      setDeletingId(null)
    }
  }

  async function showChunks(doc: DocumentInfo) {
    setPreviewLoading(true)
    setError(null)
    try {
      setPreview(await api.getChunks(doc.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : '获取切块失败')
    } finally {
      setPreviewLoading(false)
    }
  }

  const uploadBadges: Record<string, string> = lastUpload
    ? {
        ingest: formatMs(lastUpload.timings.ingest_ms),
        chunk: formatMs(lastUpload.timings.chunk_ms),
        embed: formatMs(lastUpload.timings.embed_ms),
        index: formatMs(lastUpload.timings.index_ms),
      }
    : {}

  return (
    <div className="space-y-4">
      {/* 上传区 */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-2 text-sm font-semibold text-slate-700">
          上传文档（支持 .txt / .md / .pdf，上传后自动完成入库 4 步）
        </h2>
        <PipelineSteps
          stepKeys={['ingest', 'chunk', 'embed', 'index']}
          badges={uploadBadges}
          activeKeys={lastUpload ? ['ingest', 'chunk', 'embed', 'index'] : []}
        />
        <div className="mt-3 flex items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md,.markdown,.pdf"
            disabled={uploading}
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) handleUpload(file)
            }}
            className="text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-indigo-700"
          />
          {uploading && <span className="text-sm text-slate-500">上传处理中（解析 → 切块 → 向量化 → 建索引）…</span>}
        </div>
        {lastUpload && (
          <p className="mt-2 text-xs text-emerald-600">
            「{lastUpload.document.filename}」入库成功：{lastUpload.document.num_chars} 字符 →{' '}
            {lastUpload.document.num_chunks} 个块，各步骤耗时见上方流水线。
          </p>
        )}
        {error && (
          <p className="mt-2 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>
        )}
      </section>

      {/* 文档列表 */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">
          知识库文档（{docs.length} 篇）
        </h2>
        {loading ? (
          <p className="text-sm text-slate-400">加载中…</p>
        ) : docs.length === 0 ? (
          <p className="text-sm text-slate-400">
            知识库是空的。上传一个文档，或重启后端自动导入示例文档。
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs text-slate-400">
                  <th className="py-2 pr-3 font-medium">文件名</th>
                  <th className="py-2 pr-3 font-medium">来源</th>
                  <th className="py-2 pr-3 font-medium">大小</th>
                  <th className="py-2 pr-3 font-medium">字符数</th>
                  <th className="py-2 pr-3 font-medium">块数</th>
                  <th className="py-2 pr-3 font-medium">入库时间</th>
                  <th className="py-2 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((doc) => (
                  <tr key={doc.id} className="border-b border-slate-100 last:border-0">
                    <td className="py-2.5 pr-3 font-medium text-slate-700">{doc.filename}</td>
                    <td className="py-2.5 pr-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${
                          doc.origin === 'sample'
                            ? 'bg-sky-100 text-sky-700'
                            : 'bg-violet-100 text-violet-700'
                        }`}
                      >
                        {doc.origin === 'sample' ? '示例' : '上传'}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-slate-500">{formatBytes(doc.size_bytes)}</td>
                    <td className="py-2.5 pr-3 text-slate-500">{doc.num_chars}</td>
                    <td className="py-2.5 pr-3 text-slate-500">{doc.num_chunks}</td>
                    <td className="py-2.5 pr-3 text-xs text-slate-400">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="py-2.5">
                      <div className="flex gap-2">
                        <button
                          onClick={() => showChunks(doc)}
                          disabled={previewLoading}
                          className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-600 transition-colors hover:border-indigo-300 hover:text-indigo-600"
                        >
                          查看切块
                        </button>
                        <button
                          onClick={() => handleDelete(doc)}
                          disabled={deletingId === doc.id}
                          className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-rose-500 transition-colors hover:border-rose-300 hover:bg-rose-50 disabled:opacity-50"
                        >
                          {deletingId === doc.id ? '删除中…' : '删除'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 切块预览 */}
      {preview && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">
              切块预览：{preview.document.filename}（共 {preview.chunks.length} 块，chunk_size=
              {preview.document.chunk_size}，chunk_overlap={preview.document.chunk_overlap}）
            </h2>
            <button
              onClick={() => setPreview(null)}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              关闭
            </button>
          </div>
          <p className="mb-3 text-xs text-slate-400">
            注意观察相邻块的结尾与开头：重叠部分（约 {preview.document.chunk_overlap}{' '}
            字）保证了跨块边界的句子不会被拦腰截断。
          </p>
          <div className="grid gap-2 md:grid-cols-2">
            {preview.chunks.map((chunk) => (
              <div key={chunk.chunk_id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="mb-1 flex items-center gap-2 text-xs text-slate-400">
                  <span className="rounded bg-slate-700 px-1.5 py-0.5 font-mono text-white">
                    #{chunk.chunk_index + 1}
                  </span>
                  <span>{chunk.num_chars} 字符</span>
                </div>
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-600">
                  {chunk.text}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
