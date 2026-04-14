import { useState, useCallback } from 'react'
import { useGraph } from './hooks/useGraph'
import GraphCanvas, { type ViewMode } from './components/GraphCanvas'
import DetailPanel from './components/DetailPanel'
import SearchBar from './components/SearchBar'

export default function App() {
  const { graph, loading, error, fetchNodeDetail } = useGraph()
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [view, setView] = useState<ViewMode>('overview')
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null)

  const handleNodeClick = useCallback((nodeId: string) => {
    setSelectedNodeId(nodeId)
  }, [])

  const handleCategoryClick = useCallback(
    (domain: string) => {
      if (view === 'expanded' && expandedDomain === domain) {
        // Clicking the already-expanded hub collapses back to overview
        setView('overview')
        setExpandedDomain(null)
        setSelectedNodeId(null)
        return
      }
      setExpandedDomain(domain)
      setView('expanded')
      setSelectedNodeId(null)
    },
    [view, expandedDomain],
  )

  const handleBackToOverview = useCallback(() => {
    setView('overview')
    setExpandedDomain(null)
    setSelectedNodeId(null)
  }, [])

  const handleClosePanel = useCallback(() => {
    setSelectedNodeId(null)
  }, [])

  // Search picks a node: if it's a domain, expand that domain; if it's a
  // concept/guest, jump to its domain expanded + open its detail panel.
  const handleSearchSelect = useCallback(
    (nodeId: string) => {
      if (!graph) return
      // Domain synthetic IDs use `domain:<label>`
      if (nodeId.startsWith('domain:')) {
        const label = nodeId.slice('domain:'.length)
        setExpandedDomain(label)
        setView('expanded')
        setSelectedNodeId(null)
        return
      }
      const target = graph.nodes.find((n) => n.id === nodeId)
      if (!target) return
      if (target.type === 'concept' && target.domain) {
        setExpandedDomain(target.domain)
        setView('expanded')
      } else if (target.type === 'guest') {
        // Guests may span multiple domains — find one domain where this guest
        // connects to a concept, fall back to overview if none.
        const guestEdges = graph.edges.filter((e) => e.source === nodeId || e.target === nodeId)
        const domainHit = graph.nodes.find((n) => {
          if (n.type !== 'concept') return false
          return guestEdges.some((e) => e.source === n.id || e.target === n.id)
        })?.domain
        if (domainHit) {
          setExpandedDomain(domainHit)
          setView('expanded')
        }
      }
      setSelectedNodeId(nodeId)
    },
    [graph],
  )

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      <header className="flex items-center gap-4 px-6 py-3 border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm z-40">
        <h1 className="text-lg font-bold text-white whitespace-nowrap">
          <span className="text-blue-400">Lenny</span>Verse
        </h1>

        {view === 'expanded' && (
          <button
            onClick={handleBackToOverview}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium border border-gray-700 transition-colors"
            aria-label="Back to overview"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 18l-6-6 6-6" />
            </svg>
            All categories
          </button>
        )}

        {view === 'expanded' && expandedDomain && (
          <div className="text-sm text-gray-400">
            <span className="text-gray-600">/</span>{' '}
            <span className="text-white font-semibold">{expandedDomain}</span>
          </div>
        )}

        {graph && <SearchBar nodes={graph.nodes} onSelect={handleSearchSelect} />}

        <div className="ml-auto text-xs text-gray-500">
          {graph ? `${graph.domains.length} categories · ${graph.nodes.length} items` : 'loading...'}
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
              view={view}
              expandedDomain={expandedDomain}
              onNodeClick={handleNodeClick}
              onCategoryClick={handleCategoryClick}
              selectedNodeId={selectedNodeId}
            />
          </div>
        )}

        {/* Hint pill, only shown on overview when graph is loaded */}
        {graph && view === 'overview' && (
          <div className="absolute left-1/2 top-4 -translate-x-1/2 z-20 pointer-events-none">
            <div className="px-3 py-1.5 rounded-full bg-gray-900/80 backdrop-blur-sm border border-gray-800 text-xs text-gray-400">
              Click any category to drill down into its concepts and guests
            </div>
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
