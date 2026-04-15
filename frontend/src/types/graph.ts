export interface GraphNode {
  id: string
  type: 'concept' | 'guest' | 'source' | 'domain'
  label: string
  domain: string
  confidence: number
  support_count: number
  newest_source: string
  oldest_source: string
  connections: number
  position: { x: number; y: number }
  source_type: string
  date: string
  known_for: string[]
  color: string
  url: string
  description: string
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type: 'teaches' | 'appears_in' | 'belongs_to' | 'builds_on' | 'contrasts_with' | 'debates' | 'mentioned_in'
  provenance: 'EXTRACTED' | 'INFERRED' | 'AMBIGUOUS'
  confidence: number
  label: string
}

export interface DomainSummary {
  id: string
  label: string
  color: string
  node_count: number
}

export interface GraphReport {
  god_nodes: string[]
  surprising_connections: number
  last_compiled: string
  suggested_questions: string[]
}

export interface GraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  domains: DomainSummary[]
  report: GraphReport
}

export interface NodeDetail {
  id: string
  type: string
  label: string
  domain: string
  content: string
  frontmatter: Record<string, unknown>
  connections: GraphEdge[]
  connected_nodes: GraphNode[]
}
