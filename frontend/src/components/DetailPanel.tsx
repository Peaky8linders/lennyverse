import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { NodeDetail } from '../types/graph'
import AskClaude from './AskClaude'

interface Props {
  nodeId: string | null
  fetchDetail: (id: string) => Promise<NodeDetail | null>
  onClose: () => void
  onNavigate: (nodeId: string) => void
}

export default function DetailPanel({ nodeId, fetchDetail, onClose, onNavigate }: Props) {
  const [detail, setDetail] = useState<NodeDetail | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!nodeId) {
      setDetail(null)
      return
    }
    setLoading(true)
    fetchDetail(nodeId).then((d) => {
      setDetail(d)
      setLoading(false)
    })
  }, [nodeId, fetchDetail])

  return (
    <AnimatePresence>
      {nodeId && (
        <motion.div
          initial={{ x: 400, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 400, opacity: 0 }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="fixed right-0 top-0 h-full w-96 bg-gray-900 border-l border-gray-700 shadow-2xl overflow-y-auto z-50"
        >
          <div className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                {loading ? (
                  <div className="h-6 w-40 bg-gray-800 rounded animate-pulse" />
                ) : (
                  <>
                    <h2 className="text-xl font-bold text-white">{detail?.label || nodeId}</h2>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-400 mt-1 inline-block">
                      {detail?.domain || ''}
                    </span>
                  </>
                )}
              </div>
              <button
                onClick={onClose}
                className="text-gray-500 hover:text-white transition-colors text-xl leading-none"
                aria-label="Close"
              >
                ×
              </button>
            </div>

            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-4 bg-gray-800 rounded animate-pulse" style={{ width: `${80 - i * 10}%` }} />
                ))}
              </div>
            ) : detail ? (
              <>
                <div className="text-sm text-gray-300 leading-relaxed mb-4">
                  {detail.content || 'No summary available.'}
                </div>

                {detail.connected_nodes.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-sm font-semibold text-gray-400 mb-2">Connections</h3>
                    <div className="flex flex-wrap gap-2">
                      {detail.connected_nodes.map((cn) => (
                        <button
                          key={cn.id}
                          onClick={() => onNavigate(cn.id)}
                          className="text-xs px-2 py-1 rounded-full bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors border border-gray-700"
                        >
                          {cn.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {detail.connections.filter((c) => c.type === 'contrasts_with').length > 0 && (
                  <div className="mb-4 p-3 bg-orange-950/30 border border-orange-800/30 rounded-lg">
                    <h3 className="text-sm font-semibold text-orange-400 mb-1">Tensions</h3>
                    {detail.connections
                      .filter((c) => c.type === 'contrasts_with')
                      .map((c) => (
                        <button
                          key={c.id}
                          onClick={() => onNavigate(c.source === detail.id ? c.target : c.source)}
                          className="block text-xs text-orange-300 hover:text-orange-200 mt-1"
                        >
                          {c.label || `vs ${c.source === detail.id ? c.target : c.source}`}
                        </button>
                      ))}
                  </div>
                )}

                <AskClaude contextNodeId={detail.id} />
              </>
            ) : (
              <p className="text-sm text-gray-500">Node not found.</p>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
