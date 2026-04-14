import { useState } from 'react'
import { useExplore } from '../hooks/useExplore'

interface Props {
  contextNodeId: string
}

export default function AskClaude({ contextNodeId }: Props) {
  const [question, setQuestion] = useState('')
  const { response, loading, error, ask, reset } = useExplore()

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
      {response && (
        <div className="mt-3 p-3 bg-gray-800/50 rounded-lg text-sm text-gray-300 whitespace-pre-wrap max-h-64 overflow-y-auto">
          {response}
        </div>
      )}
      {response && !loading && (
        <button onClick={reset} className="mt-2 text-xs text-gray-500 hover:text-gray-300">
          Clear
        </button>
      )}
    </div>
  )
}
