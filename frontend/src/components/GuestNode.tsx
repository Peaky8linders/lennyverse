import { memo, useState } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import { useGuestImages } from '../hooks/useGuestImages'

interface GuestNodeData {
  label: string
  color: string
  known_for: string[]
  connections: number
  confidence?: number
  id?: string
  [key: string]: unknown
}

function GuestNode({ id, data, selected }: NodeProps) {
  const d = data as GuestNodeData
  const { getGuestImage } = useGuestImages()
  const imgUrl = getGuestImage(id)
  const [imgOk, setImgOk] = useState(true)
  // Confidence fades low-support guests; clamp so they stay readable.
  const confOpacity = Math.max(0.6, Math.min(1, d.confidence ?? 1))

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
        flex flex-col items-center gap-2 transition-all duration-200
        ${selected ? 'scale-110' : 'hover:scale-105'}
      `}
      style={{ visibility: 'visible', opacity: confOpacity }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0, width: 8, height: 8 }} />
      <div className="relative">
        {imgUrl && imgOk ? (
          <img
            src={imgUrl}
            alt={d.label}
            onError={() => setImgOk(false)}
            className="w-20 h-20 rounded-full object-cover shadow-xl border-[3px]"
            style={{ borderColor: '#c084fc' }}
            draggable={false}
          />
        ) : (
          <div
            className="w-20 h-20 rounded-full flex items-center justify-center text-xl font-bold text-white shadow-xl border-[3px]"
            style={{
              background: `linear-gradient(135deg, #a855f7cc, #7e22ce88)`,
              borderColor: '#c084fc',
            }}
          >
            {initials}
          </div>
        )}
        {/* Play icon badge — indicates clickable episode content */}
        <div className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-purple-500 border-2 border-gray-900 flex items-center justify-center shadow-md">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" className="text-white ml-0.5">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      </div>
      <div className="text-sm text-gray-100 font-semibold text-center max-w-[140px] truncate">
        {d.label}
      </div>
      {d.connections > 0 && (
        <div className="text-[10px] text-purple-300/80">{d.connections} episodes</div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, width: 8, height: 8 }} />
    </div>
  )
}

export default memo(GuestNode)
