import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  useReactFlow,
  useStoreApi,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import ConceptNode from './ConceptNode'
import GuestNode from './GuestNode'
import CategoryNode from './CategoryNode'
import FlowParticles from './FlowParticles'
import type { GraphResponse } from '../types/graph'

const nodeTypes = { concept: ConceptNode, guest: GuestNode, category: CategoryNode }

export type ViewMode = 'overview' | 'expanded'

interface Props {
  graph: GraphResponse
  view: ViewMode
  expandedDomain: string | null
  onNodeClick: (nodeId: string) => void
  onCategoryClick: (domain: string) => void
  selectedNodeId: string | null
}

const DOMAIN_PREFIX = 'domain:'

/** Place items evenly on a circle centered at (0, 0). */
function radial(n: number, radius: number, startAngle = -Math.PI / 2): { x: number; y: number }[] {
  if (n === 0) return []
  if (n === 1) return [{ x: 0, y: -radius }]
  return Array.from({ length: n }, (_, i) => {
    const a = startAngle + (2 * Math.PI * i) / n
    return { x: Math.cos(a) * radius, y: Math.sin(a) * radius }
  })
}

function GraphCanvasInner({
  graph,
  view,
  expandedDomain,
  onNodeClick,
  onCategoryClick,
  selectedNodeId,
}: Props) {
  const rf = useReactFlow()
  const storeApi = useStoreApi()

  // `?beam=<node-id>` pre-seeds the hover state on mount. Lets headless
  // screenshots (and shareable deep links) capture the wisdom-beam effect
  // without having to dispatch a real mouse event.
  const forcedBeam = useMemo(() => {
    if (typeof window === 'undefined') return null
    return new URLSearchParams(window.location.search).get('beam')
  }, [])
  const [hoveredId, setHoveredId] = useState<string | null>(forcedBeam)

  // Clear hover state whenever the view changes — otherwise stale beams can
  // linger from a previous category. The URL-forced beam survives this reset.
  useEffect(() => {
    setHoveredId(forcedBeam)
  }, [view, expandedDomain, forcedBeam])

  const expandedColor = useMemo(() => {
    if (!expandedDomain) return '#a855f7'
    const d = graph.domains.find((d) => d.label === expandedDomain)
    return d?.color || '#a855f7'
  }, [graph.domains, expandedDomain])

  // ─── Overview: 7 category hubs on a circle ────────────────────────────────
  const overviewNodes = useMemo<Node[]>(() => {
    const positions = radial(graph.domains.length, 520)
    return graph.domains.map((d, i) => ({
      id: `${DOMAIN_PREFIX}${d.label}`,
      type: 'category',
      position: { x: positions[i].x - 90, y: positions[i].y - 90 },
      data: {
        label: d.label,
        color: d.color,
        count: d.node_count,
      },
      selected: false,
      draggable: false,
    }))
  }, [graph.domains])

  // ─── Expanded: hub at center, concepts inner ring, guests outer ring ──────
  const expandedNodes = useMemo<Node[]>(() => {
    if (!expandedDomain) return []
    const domain = graph.domains.find((d) => d.label === expandedDomain)
    if (!domain) return []

    // Concepts belonging to this domain
    const concepts = graph.nodes.filter(
      (n) => n.type === 'concept' && n.domain === expandedDomain,
    )

    // Guests connected to any of those concepts (teach edges)
    const conceptIds = new Set(concepts.map((c) => c.id))
    const guestIdSet = new Set<string>()
    graph.edges.forEach((e) => {
      if (conceptIds.has(e.target)) guestIdSet.add(e.source)
      if (conceptIds.has(e.source)) guestIdSet.add(e.target)
    })
    const guests = graph.nodes.filter((n) => n.type === 'guest' && guestIdSet.has(n.id))

    const nodes: Node[] = []

    // Central hub (larger, expanded state)
    nodes.push({
      id: `${DOMAIN_PREFIX}${domain.label}`,
      type: 'category',
      position: { x: -110, y: -110 },
      data: {
        label: domain.label,
        color: domain.color,
        count: domain.node_count,
        expanded: true,
      },
      selected: false,
      draggable: false,
    })

    // Inner ring: concept pills
    const conceptRadius = Math.max(320, 60 + concepts.length * 18)
    const conceptPositions = radial(concepts.length, conceptRadius, -Math.PI / 2)
    concepts.forEach((c, i) => {
      nodes.push({
        id: c.id,
        type: 'concept',
        position: { x: conceptPositions[i].x - 100, y: conceptPositions[i].y - 30 },
        data: {
          label: c.label,
          domain: c.domain,
          connections: c.connections,
          color: domain.color,
          confidence: c.confidence,
        },
        selected: c.id === selectedNodeId,
        draggable: false,
      })
    })

    // Outer ring: guest avatars
    const guestRadius = Math.max(620, conceptRadius + 280)
    const guestPositions = radial(guests.length, guestRadius, -Math.PI / 2 + 0.12)
    guests.forEach((g, i) => {
      nodes.push({
        id: g.id,
        type: 'guest',
        position: { x: guestPositions[i].x - 40, y: guestPositions[i].y - 40 },
        data: {
          label: g.label,
          domain: g.domain,
          connections: g.connections,
          color: g.color,
          confidence: g.confidence,
          known_for: g.known_for,
        },
        selected: g.id === selectedNodeId,
        draggable: false,
      })
    })

    return nodes
  }, [graph, expandedDomain, selectedNodeId])

  const nodes = view === 'overview' ? overviewNodes : expandedNodes

  // Edges: overview has none. Expanded shows concept→guest teach edges as thin wires.
  const edges = useMemo<Edge[]>(() => {
    if (view !== 'expanded' || !expandedDomain) return []
    const visibleIds = new Set(nodes.map((n) => n.id))
    const out: Edge[] = []
    graph.edges.forEach((e, idx) => {
      if (!visibleIds.has(e.source) || !visibleIds.has(e.target)) return
      if (e.source === e.target) return
      out.push({
        id: `e${idx}-${e.source}->${e.target}`,
        source: e.source,
        target: e.target,
        style:
          e.type === 'contrasts_with'
            ? { stroke: '#f97316', strokeDasharray: '6 4', strokeWidth: 1.5, opacity: 0.6 }
            : { stroke: '#6b7280', strokeWidth: 1, opacity: 0.45 },
      })
    })
    return out
  }, [graph, nodes, view, expandedDomain])

  // Force React Flow to re-measure nodes after a view change, then fit view
  useEffect(() => {
    if (nodes.length === 0) return
    const timers: number[] = []
    const runUpdate = () => {
      const state = storeApi.getState()
      const updates = new Map<string, { id: string; nodeElement: HTMLDivElement; force: true }>()
      nodes.forEach((n) => {
        const el = document.querySelector<HTMLDivElement>(`.react-flow__node[data-id="${n.id}"]`)
        if (el) updates.set(n.id, { id: n.id, nodeElement: el, force: true })
      })
      if (updates.size > 0) state.updateNodeInternals(updates)
    }
    ;[50, 200, 500].forEach((d) => timers.push(window.setTimeout(runUpdate, d)))
    timers.push(
      window.setTimeout(() => {
        rf.fitView({ padding: 0.25, duration: 500 })
      }, 650),
    )
    return () => timers.forEach((t) => window.clearTimeout(t))
  }, [nodes, storeApi, rf, view, expandedDomain])

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (node.type === 'category') {
        // Category hub: toggle expansion
        const label = (node.data as { label: string }).label
        onCategoryClick(label)
        return
      }
      onNodeClick(node.id)
    },
    [onNodeClick, onCategoryClick],
  )

  const handleNodeMouseEnter = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (view !== 'expanded') return
      // Hovering the category hub lights up every edge in the view (hero moment).
      // Hovering a concept or guest shows only the edges touching that node.
      setHoveredId(node.id)
    },
    [view],
  )

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredId(null)
  }, [])

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodeClick={handleNodeClick}
      onNodeMouseEnter={handleNodeMouseEnter}
      onNodeMouseLeave={handleNodeMouseLeave}
      nodeTypes={nodeTypes}
      minZoom={0.2}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
      nodesDraggable={false}
      nodesConnectable={false}
      fitView
      fitViewOptions={{ padding: 0.25 }}
    >
      <Background color="#1f2937" gap={40} />
      <Controls position="bottom-right" showInteractive={false} />
      <FlowParticles hoveredId={hoveredId} edges={edges} color={expandedColor} />
    </ReactFlow>
  )
}

export default function GraphCanvas(props: Props) {
  return (
    <ReactFlowProvider>
      <GraphCanvasInner {...props} />
    </ReactFlowProvider>
  )
}
