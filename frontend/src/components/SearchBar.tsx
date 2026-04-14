import { useState, useMemo } from 'react'
import type { GraphNode } from '../types/graph'

interface Props {
  nodes: GraphNode[]
  onSelect: (nodeId: string) => void
}

export default function SearchBar({ nodes, onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)

  const results = useMemo(() => {
    if (!query.trim()) return []
    const q = query.toLowerCase()
    return nodes
      .filter((n) => n.label.toLowerCase().includes(q) || n.domain.toLowerCase().includes(q))
      .slice(0, 8)
  }, [query, nodes])

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 200)}
        placeholder="Search concepts, guests..."
        className="w-64 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
      />
      {open && results.length > 0 && (
        <div className="absolute top-full mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 max-h-64 overflow-y-auto">
          {results.map((n) => (
            <button
              key={n.id}
              onMouseDown={() => { onSelect(n.id); setQuery(n.label); setOpen(false) }}
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-700 flex items-center gap-2"
            >
              <span className={`w-2 h-2 rounded-full ${n.type === 'guest' ? 'bg-purple-400' : 'bg-blue-400'}`} />
              <span className="text-white">{n.label}</span>
              <span className="text-xs text-gray-500 ml-auto">{n.domain}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
