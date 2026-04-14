import { useState, useCallback } from 'react'
import { ReactFlowProvider } from '@xyflow/react'
import { useGraph } from './hooks/useGraph'
import GraphCanvas from './components/GraphCanvas'
import DetailPanel from './components/DetailPanel'
import SearchBar from './components/SearchBar'
import DomainFilters from './components/DomainFilters'

export default function App() {
  const { graph, loading, error, fetchNodeDetail } = useGraph()
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [hiddenDomains, setHiddenDomains] = useState<Set<string>>(new Set())

  const handleNodeClick = useCallback((nodeId: string) => {
    setSelectedNodeId(nodeId)
  }, [])

  const handleClosePanel = useCallback(() => {
    setSelectedNodeId(null)
  }, [])

  const handleToggleDomain = useCallback((domain: string) => {
    setHiddenDomains((prev) => {
      const next = new Set(prev)
      if (next.has(domain)) next.delete(domain)
      else next.add(domain)
      return next
    })
  }, [])

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400 text-lg">Loading knowledge graph...</p>
        </div>
      </div>
    )
  }

  if (error || !graph) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center max-w-md">
          <h1 className="text-2xl font-bold text-white mb-2">
            <span className="text-blue-400">Lenny</span>Verse
          </h1>
          <p className="text-red-400 mb-4">{error || 'Failed to load graph'}</p>
          <p className="text-gray-500 text-sm">
            Make sure the backend is running and the wiki has been compiled.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      <header className="flex items-center gap-4 px-6 py-3 border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm z-40">
        <h1 className="text-lg font-bold text-white whitespace-nowrap">
          <span className="text-blue-400">Lenny</span>Verse
        </h1>
        <SearchBar nodes={graph.nodes} onSelect={handleNodeClick} />
        <DomainFilters
          domains={graph.domains}
          hidden={hiddenDomains}
          onToggle={handleToggleDomain}
        />
        <div className="ml-auto text-xs text-gray-500">
          {graph.nodes.length} nodes · {graph.edges.length} edges
        </div>
      </header>

      <main className="flex-1 relative">
        <ReactFlowProvider>
          <GraphCanvas
            graph={graph}
            hiddenDomains={hiddenDomains}
            onNodeClick={handleNodeClick}
            selectedNodeId={selectedNodeId}
          />
        </ReactFlowProvider>

        <DetailPanel
          nodeId={selectedNodeId}
          fetchDetail={fetchNodeDetail}
          onClose={handleClosePanel}
          onNavigate={handleNodeClick}
        />
      </main>
    </div>
  )
}
