import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'

interface GuestNodeData {
  label: string
  color: string
  known_for: string[]
  connections: number
  [key: string]: unknown
}

function GuestNode({ data, selected }: NodeProps) {
  const d = data as GuestNodeData
  const initials = d.label
    .split(' ')
    .filter((w) => w && /[A-Za-z]/.test(w[0]))
    .map((w: string) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase() || '?'

  return (
    <div
      className={`
        flex flex-col items-center gap-1 transition-all duration-200
        ${selected ? 'scale-110' : 'hover:scale-105'}
      `}
      style={{ visibility: 'visible' }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0, width: 8, height: 8 }} />
      <div className="relative">
        <div
          className="w-14 h-14 rounded-full flex items-center justify-center text-sm font-bold text-white shadow-lg border-2"
          style={{
            background: `linear-gradient(135deg, #a855f788, #a855f744)`,
            borderColor: '#a855f7',
          }}
        >
          {initials}
        </div>
        {/* Play icon badge — indicates clickable episode content */}
        <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-purple-500 border-2 border-gray-900 flex items-center justify-center shadow-md">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" className="text-white ml-0.5">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      </div>
      <div className="text-xs text-gray-200 font-medium text-center max-w-[110px] truncate mt-1">
        {d.label}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, width: 8, height: 8 }} />
    </div>
  )
}

export default memo(GuestNode)
