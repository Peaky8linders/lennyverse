import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'

interface GuestNodeData {
  label: string
  color: string
  known_for: string[]
  [key: string]: unknown
}

function GuestNode({ data, selected }: NodeProps) {
  const d = data as GuestNodeData
  const initials = d.label
    .split(' ')
    .map((w: string) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <div
      className={`
        flex flex-col items-center gap-1 transition-all duration-200
        ${selected ? 'scale-110' : 'hover:scale-105'}
      `}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0, width: 8, height: 8 }} />
      <div
        className="w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold text-white shadow-lg border-2"
        style={{
          background: `linear-gradient(135deg, ${d.color || '#a855f7'}88, ${d.color || '#a855f7'}44)`,
          borderColor: d.color || '#a855f7',
        }}
      >
        {initials}
      </div>
      <div className="text-xs text-gray-300 font-medium text-center max-w-[100px] truncate">
        {d.label}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, width: 8, height: 8 }} />
    </div>
  )
}

export default memo(GuestNode)
