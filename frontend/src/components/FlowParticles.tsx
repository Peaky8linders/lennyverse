import { useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ViewportPortal,
  useReactFlow,
  getBezierPath,
  Position,
  type Edge,
} from '@xyflow/react'

interface Props {
  /** The node the cursor is currently over, or null. */
  hoveredId: string | null
  /** All edges in the current expanded view. */
  edges: Edge[]
  /** Tint color — normally the current expanded-domain color. */
  color: string
}

/**
 * "Wisdom beams" — glowing particles stream along edges connected to the
 * currently-hovered node. Mounted inside React Flow's ViewportPortal so that
 * pan/zoom transforms are inherited automatically; path coordinates are in
 * flow space (same as node positions), no manual transform math.
 *
 * Uses SMIL `<animateMotion>` + `<mpath>` so the browser handles the motion
 * tween natively — no per-frame JS, no extra dependencies.
 */
export default function FlowParticles({ hoveredId, edges, color }: Props) {
  const rf = useReactFlow()

  // Compute bezier paths in flow coordinates for the relevant edges.
  // - Hovering a concept/guest: edges touching that node
  // - Hovering the category hub (id starts with `domain:`): every edge in view
  const paths = useMemo(() => {
    if (!hoveredId) return []

    const isHub = hoveredId.startsWith('domain:')
    const connected = isHub
      ? edges
      : edges.filter((e) => e.source === hoveredId || e.target === hoveredId)

    return connected
      .map((edge, idx) => {
        // Direction: for concept/guest hover, always flow FROM the hovered
        // node outward; for hub hover, respect the edge's declared direction.
        const outgoing = isHub || edge.source === hoveredId
        const srcId = outgoing ? edge.source : edge.target
        const tgtId = outgoing ? edge.target : edge.source

        const src = rf.getNode(srcId)
        const tgt = rf.getNode(tgtId)
        if (!src || !tgt) return null

        const sw = src.measured?.width ?? src.width ?? 120
        const sh = src.measured?.height ?? src.height ?? 60
        const tw = tgt.measured?.width ?? tgt.width ?? 120
        const th = tgt.measured?.height ?? tgt.height ?? 60

        const sx = (src.position?.x ?? 0) + sw / 2
        const sy = (src.position?.y ?? 0) + sh / 2
        const tx = (tgt.position?.x ?? 0) + tw / 2
        const ty = (tgt.position?.y ?? 0) + th / 2

        const [d] = getBezierPath({
          sourceX: sx,
          sourceY: sy,
          targetX: tx,
          targetY: ty,
          sourcePosition: Position.Bottom,
          targetPosition: Position.Top,
        })

        return { id: `wisdom-${idx}-${edge.id}`, d }
      })
      .filter((p): p is { id: string; d: string } => p !== null)
  }, [hoveredId, edges, rf])

  return (
    <ViewportPortal>
      <div
        className="wisdom-beams-layer"
        style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
      >
        <svg
          width="1"
          height="1"
          style={{ overflow: 'visible', position: 'absolute', top: 0, left: 0 }}
        >
          <defs>
            {/* Particle core: bright white center fading to the domain tint */}
            <radialGradient id="wisdom-core">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
              <stop offset="30%" stopColor="#ffffff" stopOpacity="0.95" />
              <stop offset="60%" stopColor={color} stopOpacity="0.9" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </radialGradient>
            {/* Outer halo: a dimmer, bigger radial used behind the core */}
            <radialGradient id="wisdom-halo">
              <stop offset="0%" stopColor={color} stopOpacity="0.55" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </radialGradient>
          </defs>

          <AnimatePresence>
            {hoveredId && paths.length > 0 && (
              <motion.g
                key={hoveredId}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.35 }}
              >
                {paths.map((p) => (
                  <g key={p.id}>
                    {/* Invisible path that the particles ride */}
                    <path id={p.id} d={p.d} fill="none" stroke="none" />
                    {/* Highlight stroke — brightens the edge so the beam reads even in stills */}
                    <path
                      d={p.d}
                      fill="none"
                      stroke={color}
                      strokeWidth="3"
                      strokeOpacity="0.35"
                      strokeLinecap="round"
                    />
                    <path
                      d={p.d}
                      fill="none"
                      stroke={color}
                      strokeWidth="1"
                      strokeOpacity="0.85"
                      strokeLinecap="round"
                    />
                    {/* Two staggered particles per edge; each is a halo + bright core pair */}
                    {[0, 0.9].map((delay, j) => (
                      <g key={`${p.id}-${j}`}>
                        <circle r={14} fill="url(#wisdom-halo)" opacity={0.9}>
                          <animateMotion
                            dur="1.8s"
                            repeatCount="indefinite"
                            begin={`${delay}s`}
                            rotate="auto"
                          >
                            <mpath href={`#${p.id}`} />
                          </animateMotion>
                        </circle>
                        <circle r={7} fill="url(#wisdom-core)">
                          <animateMotion
                            dur="1.8s"
                            repeatCount="indefinite"
                            begin={`${delay}s`}
                            rotate="auto"
                          >
                            <mpath href={`#${p.id}`} />
                          </animateMotion>
                        </circle>
                      </g>
                    ))}
                  </g>
                ))}
              </motion.g>
            )}
          </AnimatePresence>
        </svg>
      </div>
    </ViewportPortal>
  )
}
