import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { NodeDetail } from '../types/graph'
import AskClaude from './AskClaude'
import { useGuestImages } from '../hooks/useGuestImages'

interface Props {
  nodeId: string | null
  fetchDetail: (id: string) => Promise<NodeDetail | null>
  onClose: () => void
  onNavigate: (nodeId: string) => void
}

export default function DetailPanel({ nodeId, fetchDetail, onClose, onNavigate }: Props) {
  const [detail, setDetail] = useState<NodeDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const { getEpisodeImage } = useGuestImages()

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

                {/* For source nodes: prominent Listen on Lenny button */}
                {detail.type === 'source' && (
                  <a
                    href={(detail.frontmatter?.url as string) || `https://www.lennysnewsletter.com/p/${detail.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 w-full mb-4 px-4 py-3 rounded-lg bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400 text-white font-semibold text-sm transition-all shadow-lg shadow-purple-900/30"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                    Listen on Lenny's Newsletter
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M7 17L17 7M7 7h10v10" />
                    </svg>
                  </a>
                )}

                {/* Episode cards (for guest nodes or any node with source connections) */}
                {detail.connected_nodes.filter((cn) => cn.type === 'source').length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-sm font-semibold text-gray-400 mb-2 flex items-center gap-2">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" className="text-purple-400">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                      Episodes ({detail.connected_nodes.filter((cn) => cn.type === 'source').length})
                    </h3>
                    <div className="space-y-2">
                      {detail.connected_nodes
                        .filter((cn) => cn.type === 'source')
                        .slice(0, 10)
                        .map((cn) => {
                          const epImg = getEpisodeImage(cn.id)
                          const isNewsletter = (cn.source_type || 'podcast').toLowerCase() === 'newsletter'
                          return (
                          <a
                            key={cn.id}
                            href={cn.url || `https://www.lennysnewsletter.com/p/${cn.id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="group flex items-stretch gap-3 p-3 rounded-lg bg-gradient-to-br from-purple-950/40 to-gray-900 border border-purple-900/40 hover:border-purple-500/60 hover:from-purple-900/40 transition-all"
                          >
                            {/* Episode thumbnail tile — real cover art when available, icon fallback otherwise */}
                            {epImg ? (
                              <img
                                src={epImg}
                                alt=""
                                onError={(e) => {
                                  ;(e.currentTarget as HTMLImageElement).style.display = 'none'
                                }}
                                className="flex-shrink-0 w-14 h-14 rounded-md object-cover border border-purple-500/40 shadow-inner"
                                draggable={false}
                              />
                            ) : (
                              <div
                                className="flex-shrink-0 w-14 h-14 rounded-md flex items-center justify-center border border-purple-500/40 shadow-inner"
                                style={{
                                  background: isNewsletter
                                    ? 'linear-gradient(135deg, #7e22ce, #4338ca)'
                                    : 'linear-gradient(135deg, #a855f7, #6d28d9)',
                                }}
                              >
                                {isNewsletter ? (
                                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white">
                                    <path d="M4 4h12a2 2 0 0 1 2 2v14H6a2 2 0 0 1-2-2z" />
                                    <path d="M18 8h2a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2" />
                                    <path d="M8 8h6M8 12h6M8 16h4" />
                                  </svg>
                                ) : (
                                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white">
                                    <rect x="9" y="3" width="6" height="12" rx="3" />
                                    <path d="M5 11a7 7 0 0 0 14 0" />
                                    <path d="M12 18v3M8 21h8" />
                                  </svg>
                                )}
                              </div>
                            )}

                            <div className="flex-1 min-w-0 flex flex-col justify-center">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono uppercase tracking-wide">
                                  {cn.source_type || 'podcast'}
                                </span>
                                {cn.date && (
                                  <span className="text-[10px] text-gray-500">{cn.date}</span>
                                )}
                              </div>
                              <div className="text-xs font-medium text-white leading-snug line-clamp-2 group-hover:text-purple-200 transition-colors">
                                {cn.label}
                              </div>
                            </div>

                            <div className="flex-shrink-0 self-center w-7 h-7 rounded-full bg-purple-500/20 flex items-center justify-center group-hover:bg-purple-500/40 transition-colors">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" className="text-purple-300 ml-0.5">
                                <path d="M8 5v14l11-7z" />
                              </svg>
                            </div>
                          </a>
                          )
                        })}
                    </div>
                  </div>
                )}

                {/* Non-source connections (concepts, guests) */}
                {detail.connected_nodes.filter((cn) => cn.type !== 'source').length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-sm font-semibold text-gray-400 mb-2">Connections</h3>
                    <div className="flex flex-wrap gap-2">
                      {detail.connected_nodes
                        .filter((cn) => cn.type !== 'source')
                        .map((cn) => (
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
