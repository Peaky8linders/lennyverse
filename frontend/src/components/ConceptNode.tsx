import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import DomainIcon from './DomainIcon'

interface ConceptNodeData {
  label: string
  domain: string
  connections: number
  color: string
  confidence: number
  [key: string]: unknown
}

function ConceptNode({ data, selected }: NodeProps) {
  const d = data as ConceptNodeData
  const accent = d.color || '#3b82f6'
  // Confidence fades the node subtly — clamped so low-confidence nodes stay readable.
  const confOpacity = Math.max(0.6, Math.min(1, d.confidence || 1))

  return (
    <div
      className={`
        flex items-center gap-3 px-5 py-4 rounded-2xl border-2
        bg-gray-900/90 backdrop-blur-sm shadow-xl transition-all duration-200
        ${selected ? 'ring-2 ring-white/40 scale-105' : 'hover:scale-[1.03]'}
      `}
      style={{ borderColor: accent, minWidth: 200, maxWidth: 260, opacity: confOpacity }}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-600 !w-2 !h-2" />

      <div
        className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center border"
        style={{
          backgroundColor: `${accent}22`,
          borderColor: `${accent}66`,
          color: accent,
        }}
      >
        <DomainIcon domain={d.domain} size={22} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="text-base font-semibold text-white leading-tight truncate">
          {d.label}
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-gray-800 text-gray-400">
            {d.domain}
          </span>
          {d.connections > 0 && (
            <span className="text-[10px] text-gray-500">{d.connections} links</span>
          )}
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-gray-600 !w-2 !h-2" />
    </div>
  )
}

export default memo(ConceptNode)
