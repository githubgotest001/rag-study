import { useState } from 'react'
import KnowledgeBasePage from './pages/KnowledgeBasePage'
import QaPage from './pages/QaPage'
import SettingsPage from './pages/SettingsPage'

type Tab = 'qa' | 'kb' | 'settings'

const TABS: { key: Tab; label: string }[] = [
  { key: 'qa', label: '问答' },
  { key: 'kb', label: '知识库' },
  { key: 'settings', label: '设置与原理' },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('qa')

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div>
            <h1 className="text-lg font-bold text-slate-800">RAG 学习系统</h1>
            <p className="text-xs text-slate-400">
              检索增强生成教学示例：文档入库 → 切块 → 向量化 → 建索引 → 检索 → 增强提示词 → 生成答案
            </p>
          </div>
          <nav className="flex gap-1 rounded-xl bg-slate-100 p-1">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-colors ${
                  tab === t.key
                    ? 'bg-white text-indigo-600 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6">
        {tab === 'qa' && <QaPage />}
        {tab === 'kb' && <KnowledgeBasePage />}
        {tab === 'settings' && <SettingsPage />}
      </main>

      <footer className="mx-auto max-w-5xl px-4 pb-6 text-center text-xs text-slate-400">
        教学项目 · FastAPI + ChromaDB + sentence-transformers + React · 详见仓库 README
      </footer>
    </div>
  )
}
