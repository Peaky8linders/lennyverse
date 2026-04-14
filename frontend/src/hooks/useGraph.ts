import { useState, useEffect, useCallback } from 'react'
import type { GraphResponse, NodeDetail } from '../types/graph'

const API_BASE = import.meta.env.VITE_API_URL || ''

export function useGraph() {
  const [graph, setGraph] = useState<GraphResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchGraph = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/api/graph`)
      if (!res.ok) throw new Error(`Failed to load graph: ${res.status}`)
      const data: GraphResponse = await res.json()
      setGraph(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load graph')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchGraph()
  }, [fetchGraph])

  const fetchNodeDetail = useCallback(async (nodeId: string): Promise<NodeDetail | null> => {
    try {
      const res = await fetch(`${API_BASE}/api/node/${nodeId}`)
      if (!res.ok) return null
      return await res.json()
    } catch {
      return null
    }
  }, [])

  return { graph, loading, error, refetch: fetchGraph, fetchNodeDetail }
}
