// 相似度分数可视化：进度条 + 百分比

export default function ScoreBar({ score }: { score: number }) {
  const percent = Math.round(score * 100)
  const color =
    score >= 0.5 ? 'bg-emerald-500' : score >= 0.3 ? 'bg-amber-500' : 'bg-slate-400'
  return (
    <div className="flex items-center gap-2" title="余弦相似度（1 - 余弦距离），越大越相关">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full ${color}`} style={{ width: `${percent}%` }} />
      </div>
      <span className="font-mono text-xs text-slate-500">{score.toFixed(3)}</span>
    </div>
  )
}
