import { useState } from 'react'
import { useExplore, type RetrievalSource } from '../hooks/useExplore'

interface Props {
  contextNodeId: string
  onNavigate?: (nodeId: string) => void
}

function confidenceColor(conf: number): string {
  if (conf >= 0.7) return '#34d399' // emerald
  if (conf >= 0.4) return '#f59e0b' // amber
  return '#f87171' // rose
}

function SourceCard({ src, onNavigate }: { src: RetrievalSource; onNavigate?: (id: string) => void }) {
  const pct = Math.round(src.confidence * 100)
  const color = confidenceColor(src.confidence)
  const typeLabel = src.node_type.toUpperCase()
  const clickable = Boolean(onNavigate)
  return (
    <button
      type="button"
      disabled={!clickable}
      onClick={() => onNavigate?.(src.node_id)}
      className={
        'group text-left w-full rounded-md border border-gray-700/60 bg-gray-900/40 ' +
        'px-2.5 py-2 transition-all ' +
        (clickable ? 'hover:border-purple-500/60 hover:bg-purple-950/30 cursor-pointer' : 'cursor-default')
      }
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-[9px] uppercase tracking-wider text-gray-500">{typeLabel}</span>
        <div className="flex items-center gap-1.5">
          <div className="h-1 w-8 bg-gray-800 rounded-full overflow-hidden">
            <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
          </div>
          <span className="text-[10px] text-gray-500 tabular-nums">{pct}%</span>
        </div>
      </div>
      <div className="text-xs text-gray-200 font-medium truncate group-hover:text-white">
        {src.title}
      </div>
      {src.snippet && (
        <div className="text-[11px] text-gray-500 mt-0.5 line-clamp-2">{src.snippet}</div>
      )}
    </button>
  )
}

export default function AskClaude({ contextNodeId, onNavigate }: Props) {
  const [question, setQuestion] = useState('')
  const { response, sources, loading, error, ask, reset } = useExplore()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || loading) return
    ask(question.trim(), contextNodeId)
  }

  return (
    <div className="mt-4 border-t border-gray-700 pt-4">
      <h4 className="text-sm font-semibold text-gray-300 mb-2">Ask Claude</h4>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Go deeper on this topic..."
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm rounded-lg transition-colors"
        >
          {loading ? '...' : 'Ask'}
        </button>
      </form>
      {error && (
        <p className="mt-2 text-sm text-red-400">{error}</p>
      )}

      {/* Retrieved sources — arrives before the LLM response via the SSE `sources` event */}
      {sources.length > 0 && (
        <div className="mt-3">
          <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-1.5">
            Grounded in {sources.length} source{sources.length !== 1 ? 's' : ''}
          </div>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {sources.map((s) => (
              <SourceCard key={s.node_id} src={s} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      )}

      {response && (
        <div className="mt-3 p-3 bg-gray-800/50 rounded-lg text-sm text-gray-300 whitespace-pre-wrap max-h-64 overflow-y-auto">
          {response}
        </div>
      )}
      {(response || sources.length > 0) && !loading && (
        <button onClick={reset} className="mt-2 text-xs text-gray-500 hover:text-gray-300">
          Clear
        </button>
      )}
    </div>
  )
}
