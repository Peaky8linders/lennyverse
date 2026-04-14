import { useCallback, useEffect, useMemo } from 'react'
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useReactFlow,
  useStoreApi,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import ConceptNode from './ConceptNode'
import GuestNode from './GuestNode'
import type { GraphResponse } from '../types/graph'

const nodeTypes = { concept: ConceptNode, guest: GuestNode }

interface Props {
  graph: GraphResponse
  hiddenDomains: Set<string>
  onNodeClick: (nodeId: string) => void
  selectedNodeId: string | null
}

function GraphCanvasInner({ graph, hiddenDomains, onNodeClick, selectedNodeId }: Props) {
  const rf = useReactFlow()
  const storeApi = useStoreApi()

  const nodes = useMemo<Node[]>(() => {
    return graph.nodes
      .filter((n) => n.type !== 'source' && !hiddenDomains.has(n.domain))
      .map((n) => ({
        id: n.id,
        type: n.type === 'guest' ? 'guest' : 'concept',
        position: n.position,
        data: {
          label: n.label,
          domain: n.domain,
          connections: n.connections,
          color: n.color,
          confidence: n.confidence,
          known_for: n.known_for,
        },
        selected: n.id === selectedNodeId,
      }))
  }, [graph, hiddenDomains, selectedNodeId])

  const edges = useMemo<Edge[]>(() => {
    const visibleIds = new Set(nodes.map((n) => n.id))
    const seen = new Set<string>()
    const out: Edge[] = []
    graph.edges
      .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target) && e.source !== e.target)
      .forEach((e, idx) => {
        const id = `e${idx}-${e.source}->${e.target}`
        if (seen.has(id)) return
        seen.add(id)
        out.push({
          id,
          source: e.source,
          target: e.target,
          style: e.type === 'contrasts_with'
            ? { stroke: '#f97316', strokeDasharray: '6 4', strokeWidth: 2 }
            : { stroke: '#9ca3af', strokeWidth: 1.5 },
        })
      })
    return out
  }, [graph, nodes])

  // Force React Flow to measure all nodes + register handles.
  // Workaround for a case where the ResizeObserver doesn't fire on initial mount
  // (happens when the container was 0x0 when ReactFlow mounted).
  useEffect(() => {
    if (nodes.length === 0) return
    const timers: number[] = []
    const runUpdate = () => {
      const state = storeApi.getState()
      const updates = new Map<string, { id: string; nodeElement: HTMLElement; force: true }>()
      nodes.forEach((n) => {
        const el = document.querySelector<HTMLElement>(`.react-flow__node[data-id="${n.id}"]`)
        if (el) updates.set(n.id, { id: n.id, nodeElement: el, force: true })
      })
      if (updates.size > 0) {
        state.updateNodeInternals(updates)
      }
    }
    // Retry a few times to handle race conditions with DOM paint
    ;[50, 200, 500].forEach((d) => {
      timers.push(window.setTimeout(runUpdate, d))
    })
    timers.push(window.setTimeout(() => {
      rf.fitView({ padding: 0.2, duration: 400 })
    }, 750))
    return () => timers.forEach((t) => window.clearTimeout(t))
  }, [nodes, storeApi, rf])

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeClick(node.id)
    },
    [onNodeClick],
  )

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodeClick={handleNodeClick}
      nodeTypes={nodeTypes}
      minZoom={0.1}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
      nodesDraggable={false}
      nodesConnectable={false}
      fitView
      fitViewOptions={{ padding: 0.2 }}
    >
      <Background color="#1f2937" gap={40} />
      <Controls position="bottom-right" />
      <MiniMap
        nodeColor={(n) => {
          const data = n.data as Record<string, unknown>
          return (data?.color as string) || '#4b5563'
        }}
        maskColor="rgba(0,0,0,0.7)"
        position="bottom-right"
        style={{ marginBottom: 60 }}
      />
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
