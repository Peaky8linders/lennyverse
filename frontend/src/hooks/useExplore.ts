import { useState, useCallback, useRef } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || ''

export interface RetrievalSource {
  node_id: string
  node_type: string
  title: string
  snippet: string
  confidence: number
  score: number
  bm25_rank: number | null
  graph_rank: number | null
}

export function useExplore() {
  const [response, setResponse] = useState('')
  const [sources, setSources] = useState<RetrievalSource[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const ask = useCallback(async (question: string, contextNodeId: string = '') => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setLoading(true)
    setError(null)
    setResponse('')
    setSources([])

    try {
      const res = await fetch(`${API_BASE}/api/explore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, context_node_id: contextNodeId }),
        signal: controller.signal,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }))
        throw new Error(err.detail || `Error ${res.status}`)
      }

      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulated = ''

      // SSE frame parser: tracks the current event name so `event: sources`
      // payloads don't get lost in the token stream. Frames are separated
      // by a blank line; inside a frame we collect event: / data: lines.
      let currentEvent: string | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line === '') {
            currentEvent = null
            continue
          }
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
            continue
          }
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (currentEvent === 'sources' && Array.isArray(data.sources)) {
                setSources(data.sources as RetrievalSource[])
              } else if (currentEvent === 'error') {
                throw new Error(data.detail || 'Stream error')
              } else if (data.text) {
                accumulated += data.text
                setResponse(accumulated)
              }
            } catch (err) {
              // Re-throw stream errors; skip malformed JSON silently
              if (err instanceof Error && err.message !== 'Stream error') {
                // swallow JSON parse errors on partial frames
              } else {
                throw err
              }
            }
          }
        }
      }
    } catch (e) {
      if (!controller.signal.aborted) {
        setError(e instanceof Error ? e.message : 'Something went wrong')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setResponse('')
    setSources([])
    setError(null)
  }, [])

  return { response, sources, loading, error, ask, reset }
}
