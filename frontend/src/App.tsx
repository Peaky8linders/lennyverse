import { useState, useCallback } from 'react'
import { useGraph } from './hooks/useGraph'
import GraphCanvas from './components/GraphCanvas'
import DetailPanel from './components/DetailPanel'
import SearchBar from './components/SearchBar'

export default function App() {
  const { graph, loading, error, fetchNodeDetail } = useGraph()
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  const handleNodeClick = useCallback((nodeId: string) => {
    setSelectedNodeId(nodeId)
  }, [])

  const handleClosePanel = useCallback(() => {
    setSelectedNodeId(null)
  }, [])

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      <header className="flex items-center gap-4 px-6 py-3 border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm z-40">
        <h1 className="text-lg font-bold text-white whitespace-nowrap">
          <span className="text-blue-400">Lenny</span>Verse
        </h1>
        {graph && <SearchBar nodes={graph.nodes} onSelect={handleNodeClick} />}
        <div className="ml-auto text-xs text-gray-500">
          {graph ? `${graph.nodes.length} nodes · ${graph.edges.length} edges` : 'loading...'}
        </div>
      </header>

      <main className="flex-1 relative" style={{ minHeight: 0 }}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
            <div className="text-center">
              <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-gray-400 text-lg">Loading knowledge graph...</p>
            </div>
          </div>
        )}

        {error && !graph && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="text-center max-w-md">
              <p className="text-red-400 mb-4">{error}</p>
              <p className="text-gray-500 text-sm">
                Make sure the backend is running and the wiki has been compiled.
              </p>
            </div>
          </div>
        )}

        {graph && (
          <div className="absolute inset-0">
            <GraphCanvas
              graph={graph}
              onNodeClick={handleNodeClick}
              selectedNodeId={selectedNodeId}
            />
          </div>
        )}

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
