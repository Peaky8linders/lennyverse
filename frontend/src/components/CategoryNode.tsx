import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import DomainIcon from './DomainIcon'

interface CategoryNodeData {
  label: string
  color: string
  count: number
  expanded?: boolean
  dimmed?: boolean
  [key: string]: unknown
}

function CategoryNode({ data, selected }: NodeProps) {
  const d = data as CategoryNodeData
  const accent = d.color || '#3b82f6'
  const size = d.expanded ? 220 : 180
  const opacity = d.dimmed ? 0.35 : 1

  return (
    <div
      className={`
        group relative flex flex-col items-center justify-center gap-2
        rounded-full border-[3px] cursor-pointer transition-all duration-300
        ${selected ? 'ring-4 ring-white/30 scale-105' : 'hover:scale-[1.04]'}
      `}
      style={{
        width: size,
        height: size,
        borderColor: accent,
        background: `radial-gradient(circle at 30% 30%, ${accent}33, ${accent}11 70%), #0b1020`,
        boxShadow: `0 0 40px ${accent}33, inset 0 0 20px ${accent}22`,
        opacity,
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />

      <div
        className="flex items-center justify-center rounded-2xl"
        style={{
          width: 68,
          height: 68,
          backgroundColor: `${accent}26`,
          color: accent,
          border: `1.5px solid ${accent}55`,
        }}
      >
        <DomainIcon domain={d.label} size={36} />
      </div>

      <div className="text-base font-bold text-white text-center px-4 leading-tight">
        {d.label}
      </div>

      <div
        className="text-[11px] font-medium uppercase tracking-wider"
        style={{ color: accent }}
      >
        {d.count} {d.count === 1 ? 'item' : 'items'}
      </div>

      {!d.expanded && !d.dimmed && (
        <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
          <div
            className="text-[10px] px-2 py-0.5 rounded-full bg-gray-900 border whitespace-nowrap"
            style={{ borderColor: `${accent}66`, color: accent }}
          >
            click to expand
          </div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  )
}

export default memo(CategoryNode)
