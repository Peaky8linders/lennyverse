import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'

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
  const borderColor = d.color || '#3b82f6'

  return (
    <div
      className={`
        px-4 py-3 rounded-xl border-2 bg-gray-900/90 backdrop-blur-sm
        shadow-lg transition-all duration-200
        ${selected ? 'ring-2 ring-white/30 scale-105' : 'hover:scale-102'}
      `}
      style={{ borderColor, minWidth: 120, maxWidth: 200 }}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-600 !w-2 !h-2" />
      <div className="text-sm font-semibold text-white truncate">{d.label}</div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-xs px-1.5 py-0.5 rounded-full bg-gray-800 text-gray-400">
          {d.domain}
        </span>
        {d.connections > 0 && (
          <span className="text-xs text-gray-500">{d.connections} links</span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-gray-600 !w-2 !h-2" />
    </div>
  )
}

export default memo(ConceptNode)
