import { useCallback, useEffect } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import ConceptNode from './ConceptNode'
import GuestNode from './GuestNode'
import TensionEdge from './TensionEdge'
import type { GraphResponse } from '../types/graph'

const nodeTypes = { concept: ConceptNode, guest: GuestNode }
const edgeTypes = { tension: TensionEdge }

interface Props {
  graph: GraphResponse
  hiddenDomains: Set<string>
  onNodeClick: (nodeId: string) => void
  selectedNodeId: string | null
}

export default function GraphCanvas({ graph, hiddenDomains, onNodeClick, selectedNodeId }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  useEffect(() => {
    const newNodes: Node[] = graph.nodes
      .filter((n) => !hiddenDomains.has(n.domain))
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

    const visibleIds = new Set(newNodes.map((n) => n.id))
    const newEdges: Edge[] = graph.edges
      .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
      .map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.type === 'contrasts_with' ? 'tension' : 'default',
        data: { type: e.type, label: e.label, provenance: e.provenance },
        animated: e.type === 'contrasts_with',
        style: e.type === 'contrasts_with'
          ? { stroke: '#f97316', strokeDasharray: '6 4' }
          : { stroke: '#4b5563' },
      }))

    setNodes(newNodes)
    setEdges(newEdges)
  }, [graph, hiddenDomains, selectedNodeId, setNodes, setEdges])

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
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={handleNodeClick}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      fitView
      minZoom={0.1}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
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
