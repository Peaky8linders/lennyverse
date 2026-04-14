import { type EdgeProps, getBezierPath } from '@xyflow/react'

export default function TensionEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  selected,
}: EdgeProps) {
  const [edgePath] = getBezierPath({
    sourceX, sourceY, targetX, targetY,
    sourcePosition, targetPosition,
  })

  const strokeColor = '#f97316'
  const dashArray = '6 4'
  const strokeWidth = selected ? 2.5 : 2

  return (
    <path
      id={id}
      d={edgePath}
      fill="none"
      stroke={strokeColor}
      strokeWidth={strokeWidth}
      strokeDasharray={dashArray}
      className="transition-all duration-200"
      style={{ opacity: selected ? 1 : 0.6 }}
    />
  )
}
