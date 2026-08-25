import { useState } from 'react'
import { api } from '../api'
import PipelineSteps from '../components/PipelineSteps'
import ScoreBar from '../components/ScoreBar'
import type { QueryResponse } from '../types'
import { formatMs } from '../utils'

const SAMPLE_QUESTIONS = [
  '什么是 RAG？它解决了什么问题？',
  'chunk_overlap 重叠有什么作用？',
  '余弦相似度是怎么计算的？',
  '没有大语言模型时 RAG 还能用吗？',
]

const MODE_LABEL: Record<QueryResponse['mode'], string> = {
  llm: 'LLM 生成',
  extractive: '检索片段拼接（未使用 LLM）',
  empty: '知识库为空',
}

export default function QaPage() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<QueryResponse | null>(null)
  const [showPrompt, setShowPrompt] = useState(false)

  async function ask(q?: string) {
    const text = (q ?? question).trim()
    if (!text) {
      setError('请先输入问题')
      return
    }
    setQuestion(text)
    setLoading(true)
    setError(null)
    setResult(null)
    setShowPrompt(false)
    try {
      setResult(await api.query(text))
    } catch (e) {
      setError(e instanceof Error ? e.message : '请求失败')
    } finally {
      setLoading(false)
    }
  }

  const timingBadges: Record<string, string> = {}
  if (result) {
    if (result.timings.embed_ms != null) timingBadges.embed = formatMs(result.timings.embed_ms)
    if (result.timings.retrieve_ms != null)
      timingBadges.retrieve = formatMs(result.timings.retrieve_ms)
    if (result.timings.generate_ms != null) {
      timingBadges.augment = '<1ms'
      timingBadges.generate = formatMs(result.timings.generate_ms)
    }
  }

  return (
    <div className="space-y-4">
      {/* 流水线可视化 */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-2 text-sm font-semibold text-slate-700">
          RAG 问答链路（提问后会显示各步骤耗时，鼠标悬停查看说明）
        </h2>
        <PipelineSteps
          badges={timingBadges}
          activeKeys={result ? ['embed', 'retrieve', 'augment', 'generate'] : []}
        />
        <p className="mt-2 text-xs text-slate-400">
          前 4 步（入库 → 切块 → 向量化 → 建索引）在「知识库」页面上传文档时完成；提问时执行后
          3 步：问题向量化 → 检索 → 增强提示词并生成答案。
        </p>
      </section>

      {/* 提问区 */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !loading && ask()}
            placeholder="输入你的问题，例如：什么是 RAG？"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
          />
          <button
            onClick={() => ask()}
            disabled={loading}
            className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? '思考中…' : '提问'}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {SAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => ask(q)}
              disabled={loading}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600 transition-colors hover:border-indigo-300 hover:text-indigo-600 disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
        {error && (
          <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>
        )}
      </section>

      {/* 答案区 */}
      {result && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-700">答案</h2>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                result.mode === 'llm'
                  ? 'bg-emerald-100 text-emerald-700'
                  : result.mode === 'extractive'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-slate-100 text-slate-500'
              }`}
            >
              {MODE_LABEL[result.mode]}
              {result.model ? `（${result.model}）` : ''}
            </span>
          </div>
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
            {result.answer}
          </div>

          {result.prompt && (
            <div className="mt-4">
              <button
                onClick={() => setShowPrompt(!showPrompt)}
                className="text-xs font-medium text-indigo-600 hover:underline"
              >
                {showPrompt ? '收起' : '展开'}增强后的完整 Prompt（步骤 6：Augment）
              </button>
              {showPrompt && (
                <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-900 p-3 text-xs leading-relaxed text-slate-100">
                  {result.prompt}
                </pre>
              )}
            </div>
          )}
        </section>
      )}

      {/* 引用来源 */}
      {result && result.citations.length > 0 && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            引用来源（检索到的 {result.citations.length} 个文本块，按相似度降序）
          </h2>
          <div className="space-y-3">
            {result.citations.map((c) => (
              <div key={c.ref} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="mb-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span className="rounded bg-indigo-600 px-1.5 py-0.5 font-mono text-xs font-bold text-white">
                    [{c.ref}]
                  </span>
                  <span className="text-xs font-medium text-slate-700">{c.source}</span>
                  <span className="text-xs text-slate-400">第 {c.chunk_index + 1} 块</span>
                  <ScoreBar score={c.score} />
                </div>
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-600">
                  {c.text}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
