// RAG 七步流水线可视化组件（教学核心）

export interface StepDef {
  key: string
  cn: string
  en: string
  desc: string
}

/** RAG 的完整七个步骤（入库 4 步 + 问答 3 步） */
export const RAG_STEPS: StepDef[] = [
  { key: 'ingest', cn: '文档入库', en: 'Ingest', desc: '解析 txt / markdown / pdf 为纯文本' },
  { key: 'chunk', cn: '切块', en: 'Chunk', desc: '按 chunk_size 切成带重叠的小块' },
  { key: 'embed', cn: '向量化', en: 'Embed', desc: '用 embedding 模型把文本变成语义向量' },
  { key: 'index', cn: '建索引', en: 'Index', desc: '向量与原文写入 ChromaDB 向量库' },
  { key: 'retrieve', cn: '检索', en: 'Retrieve', desc: '用问题向量找出最相似的 top_k 个块' },
  { key: 'augment', cn: '增强提示词', en: 'Augment', desc: '把检索片段按模板拼进 prompt' },
  { key: 'generate', cn: '生成答案', en: 'Generate', desc: 'LLM 生成（或检索片段拼接兜底）' },
]

interface Props {
  /** 只展示这些步骤（默认全部 7 步） */
  stepKeys?: string[]
  /** 每个步骤的耗时标注，例如 { embed: '12ms' } */
  badges?: Record<string, string>
  /** 高亮显示的步骤 */
  activeKeys?: string[]
}

export default function PipelineSteps({ stepKeys, badges = {}, activeKeys = [] }: Props) {
  const steps = stepKeys
    ? RAG_STEPS.filter((s) => stepKeys.includes(s.key))
    : RAG_STEPS

  return (
    <div className="flex flex-wrap items-stretch gap-1.5">
      {steps.map((step, i) => {
        const active = activeKeys.includes(step.key)
        return (
          <div key={step.key} className="flex items-center gap-1.5">
            <div
              title={step.desc}
              className={`rounded-lg border px-2.5 py-1.5 text-center transition-colors ${
                active
                  ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
                  : 'border-slate-200 bg-white text-slate-600'
              }`}
            >
              <div className="text-xs font-semibold leading-tight">
                {step.cn}
                <span className="ml-1 font-normal text-[10px] opacity-60">{step.en}</span>
              </div>
              {badges[step.key] && (
                <div className="mt-0.5 text-[10px] font-mono text-indigo-500">
                  {badges[step.key]}
                </div>
              )}
            </div>
            {i < steps.length - 1 && <span className="text-slate-300">→</span>}
          </div>
        )
      })}
    </div>
  )
}
