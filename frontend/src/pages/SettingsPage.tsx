import { useEffect, useState } from 'react'
import { api } from '../api'
import type { HealthInfo, SettingsInfo } from '../types'

/** 每个 RAG 步骤对应的代码位置（教学对照表） */
const CODE_MAP = [
  { step: '1. Ingest 文档入库', file: 'backend/app/rag/loading.py', desc: '解析 txt / markdown / pdf 为纯文本' },
  { step: '2. Chunk 切块', file: 'backend/app/rag/chunking.py', desc: '句子感知的滑动窗口切块，可配置 chunk_size / chunk_overlap' },
  { step: '3. Embed 向量化', file: 'backend/app/rag/embedding.py', desc: 'sentence-transformers 把文本编码成 384 维语义向量' },
  { step: '4. Index 建索引', file: 'backend/app/rag/vectorstore.py', desc: '向量 + 原文 + 元数据写入 ChromaDB（持久化）' },
  { step: '5. Retrieve 检索', file: 'backend/app/rag/vectorstore.py', desc: '余弦相似度近邻搜索，取 top_k 个最相关块' },
  { step: '6. Augment 增强提示词', file: 'backend/app/rag/generation.py', desc: '把检索片段按模板拼进 prompt，要求“只根据资料回答”' },
  { step: '7. Generate 生成答案', file: 'backend/app/rag/generation.py', desc: 'LLM 生成；无 API Key 时降级为句子级抽取式回答' },
]

function Item({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="mt-0.5 font-mono text-sm font-medium text-slate-700">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </div>
  )
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsInfo | null>(null)
  const [health, setHealth] = useState<HealthInfo | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.settings(), api.health()])
      .then(([s, h]) => {
        setSettings(s)
        setHealth(h)
      })
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
  }, [])

  if (error) {
    return <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>
  }
  if (!settings) {
    return <p className="text-sm text-slate-400">加载中…</p>
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-1 text-sm font-semibold text-slate-700">当前运行配置（只读）</h2>
        <p className="mb-3 text-xs text-slate-400">
          修改方式：编辑 backend/.env（参考 backend/.env.example）后重启后端。密钥永远不会返回给前端。
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Item
            label="chunk_size 块大小"
            value={`${settings.chunk_size} 字符`}
            hint="每个文本块的最大字符数，太小丢上下文，太大语义不聚焦"
          />
          <Item
            label="chunk_overlap 块重叠"
            value={`${settings.chunk_overlap} 字符`}
            hint="相邻块共享的结尾/开头文本，保护跨边界的关键句子"
          />
          <Item
            label="top_k 检索数量"
            value={`${settings.top_k} 个块`}
            hint="每次提问检索的最相似块数，太小漏资料，太大引入噪音"
          />
          <Item
            label="Embedding 模型"
            value={settings.embedding_model}
            hint="问题与文档必须用同一个模型向量化"
          />
          <Item
            label="LLM 生成"
            value={
              settings.llm_active
                ? `已启用（${settings.openai_model}）`
                : settings.llm_enabled
                  ? '未配置 API Key（走抽取式回答）'
                  : '已关闭（LLM_ENABLED=false）'
            }
            hint="配置 OPENAI_API_KEY 后自动切换为真正的 LLM 生成"
          />
          <Item
            label="OpenAI 兼容服务地址"
            value={settings.openai_base_url ?? '默认（api.openai.com）'}
            hint={`API Key 状态：${settings.openai_api_key_set ? '已配置' : '未配置'}`}
          />
        </div>
      </section>

      {health && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">运行状态</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <Item label="知识库文档数" value={`${health.num_documents} 篇`} />
            <Item label="向量库块数" value={`${health.num_chunks} 个`} />
            <Item
              label="Embedding 模型"
              value={health.embedding_model_loaded ? '已加载' : '未加载（首次使用时加载）'}
            />
          </div>
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">
          RAG 七步 × 代码对照（想深入学习就从这些文件读起）
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs text-slate-400">
                <th className="py-2 pr-3 font-medium">步骤</th>
                <th className="py-2 pr-3 font-medium">代码位置</th>
                <th className="py-2 font-medium">说明</th>
              </tr>
            </thead>
            <tbody>
              {CODE_MAP.map((row) => (
                <tr key={row.step} className="border-b border-slate-100 last:border-0">
                  <td className="py-2.5 pr-3 font-medium text-slate-700">{row.step}</td>
                  <td className="py-2.5 pr-3">
                    <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-indigo-600">
                      {row.file}
                    </code>
                  </td>
                  <td className="py-2.5 text-xs text-slate-500">{row.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
