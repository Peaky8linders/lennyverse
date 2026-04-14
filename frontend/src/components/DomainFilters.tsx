import type { DomainSummary } from '../types/graph'

interface Props {
  domains: DomainSummary[]
  hidden: Set<string>
  onToggle: (domain: string) => void
}

export default function DomainFilters({ domains, hidden, onToggle }: Props) {
  return (
    <div className="flex gap-2 flex-wrap">
      {domains.map((d) => {
        const isHidden = hidden.has(d.label)
        return (
          <button
            key={d.id}
            onClick={() => onToggle(d.label)}
            className={`
              px-3 py-1 rounded-full text-xs font-medium transition-all border
              ${isHidden
                ? 'bg-gray-800 text-gray-500 border-gray-700 opacity-50'
                : 'text-white border-transparent'}
            `}
            style={isHidden ? {} : { backgroundColor: d.color + '33', borderColor: d.color }}
          >
            {d.label} ({d.node_count})
          </button>
        )
      })}
    </div>
  )
}
