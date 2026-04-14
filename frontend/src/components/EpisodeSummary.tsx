import { useEffect, useState } from 'react'
import type { NodeDetail } from '../types/graph'
import { useGuestImages } from '../hooks/useGuestImages'

interface Props {
  episodeId: string
  parentLabel?: string
  fetchDetail: (id: string) => Promise<NodeDetail | null>
  onBack: () => void
  onNavigate: (nodeId: string) => void
}

/** "Hard truths about building in the AI era | Keith Rabois (Khosla Ventures)"
 *  → "Hard truths about building in the AI era"                                */
function cleanTitle(raw: string | undefined): string {
  if (!raw) return ''
  return raw.split('|')[0].trim()
}

/** Parse the episode's one-line description into a hook + a list of topics.
 *  The starter pack descriptions follow a reliable shape:
 *    "<Hook sentence>, covering <topic A>, <topic B>, and <topic C>."
 *  If the "covering" clause is missing, we keep the whole thing as the hook.
 */
function parseIdeas(content: string): { hook: string; topics: string[] } {
  if (!content) return { hook: '', topics: [] }
  const text = content.trim()
  const coverMatch = text.match(/^(.*?),\s*covering\s+(.+?)\.?$/i)
  if (!coverMatch) return { hook: text.replace(/\.$/, ''), topics: [] }
  const hook = coverMatch[1].trim().replace(/\.$/, '')
  const rawTopics = coverMatch[2]
    .replace(/,\s*and\s+/gi, ', ')
    .replace(/\s+and\s+/gi, ', ')
  const topics = rawTopics
    .split(',')
    .map((t) => t.trim().replace(/\.$/, ''))
    .filter(Boolean)
    .map((t) =>
      t
        .split(/\s+/)
        .map((w) => (w.length > 3 ? w.charAt(0).toUpperCase() + w.slice(1) : w))
        .join(' ')
        .replace(/^./, (c) => c.toUpperCase()),
    )
  return { hook, topics }
}

/** Convert a slug id → a Title Case label. "career-development" → "Career Development" */
function slugLabel(slug: string): string {
  return slug
    .replace(/^ep-/, '')
    .split('-')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export default function EpisodeSummary({
  episodeId,
  parentLabel,
  fetchDetail,
  onBack,
  onNavigate,
}: Props) {
  const [detail, setDetail] = useState<NodeDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const { getEpisodeImage } = useGuestImages()

  useEffect(() => {
    setLoading(true)
    fetchDetail(episodeId).then((d) => {
      setDetail(d)
      setLoading(false)
    })
  }, [episodeId, fetchDetail])

  const img = getEpisodeImage(episodeId)
  const fm = (detail?.frontmatter ?? {}) as {
    date?: string
    url?: string
    guests?: string[]
    concepts?: string[]
    source_type?: string
    word_count?: number
  }

  const title = cleanTitle(detail?.label)
  const { hook, topics } = parseIdeas(detail?.content || '')
  const guestSlug = Array.isArray(fm.guests) && fm.guests[0] ? fm.guests[0] : null
  const guestName = guestSlug ? slugLabel(guestSlug) : null

  // Real Lenny URL: the compiler's url_map fallback is a Google search link,
  // which is ugly but does land the user on the episode. Prefer frontmatter.url.
  const lennyUrl = fm.url || `https://www.lennysnewsletter.com/p/${episodeId.replace(/^ep-/, '')}`

  return (
    <div className="p-6 flex flex-col gap-4">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors -ml-1"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 18l-6-6 6-6" />
        </svg>
        Back{parentLabel ? ` to ${parentLabel}` : ''}
      </button>

      {loading && !detail && (
        <div className="space-y-3">
          <div className="aspect-square bg-gray-800 rounded-xl animate-pulse" />
          <div className="h-6 bg-gray-800 rounded animate-pulse" />
          <div className="h-3 bg-gray-800 rounded animate-pulse w-2/3" />
          <div className="h-20 bg-gray-800 rounded animate-pulse" />
        </div>
      )}

      {detail && (
        <>
          {/* Cover art hero */}
          {img && (
            <div
              className="relative rounded-xl overflow-hidden border border-purple-900/40 shadow-xl"
              style={{ boxShadow: '0 20px 60px -20px rgba(168, 85, 247, 0.35)' }}
            >
              <img src={img} alt="" className="w-full aspect-square object-cover" draggable={false} />
              <div className="absolute inset-0 bg-gradient-to-t from-gray-950/80 via-transparent to-transparent" />
              <div className="absolute top-3 left-3 flex items-center gap-2">
                <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/30 backdrop-blur text-purple-100 font-mono uppercase tracking-wide border border-purple-400/30">
                  {fm.source_type || 'podcast'}
                </span>
                {fm.date && (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-black/50 backdrop-blur text-gray-200 font-mono">
                    {fm.date}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Title + guest */}
          <div>
            <h2 className="text-lg font-bold text-white leading-tight">{title}</h2>
            {guestName && (
              <p className="text-sm text-purple-300 mt-1 font-medium">{guestName}</p>
            )}
            {typeof fm.word_count === 'number' && fm.word_count > 0 && (
              <p className="text-[11px] text-gray-500 mt-1">
                {fm.word_count.toLocaleString()} words · approx {Math.round(fm.word_count / 150)} min read
              </p>
            )}
          </div>

          {/* Hook — the lead sentence of the episode, pulled verbatim */}
          {hook && (
            <div className="relative pl-4">
              <div className="absolute left-0 top-1 bottom-1 w-[3px] rounded bg-gradient-to-b from-purple-400 to-purple-700" />
              <p className="text-sm text-gray-200 italic leading-snug">{hook}</p>
            </div>
          )}

          {/* Main ideas extracted from the description's "covering" clause */}
          {topics.length > 0 && (
            <div>
              <h3 className="flex items-center gap-1.5 text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-purple-400">
                  <path d="M2 12h20M12 2l4 4-4 4M12 22l-4-4 4-4" />
                </svg>
                Main ideas
              </h3>
              <ul className="space-y-1.5">
                {topics.map((t, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-200">
                    <span className="mt-2 w-1 h-1 rounded-full bg-purple-400 flex-shrink-0" />
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Concept tag chips — clickable, jump to the concept node */}
          {Array.isArray(fm.concepts) && fm.concepts.length > 0 && (
            <div>
              <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
                Linked concepts
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {fm.concepts.map((cid) => (
                  <button
                    key={cid}
                    onClick={() => onNavigate(cid)}
                    className="text-[11px] px-2 py-1 rounded-full bg-gray-800 text-gray-300 hover:bg-purple-900/40 hover:text-purple-100 transition-colors border border-gray-700 hover:border-purple-500/60"
                  >
                    {slugLabel(cid)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Listen CTA */}
          <a
            href={lennyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full mt-2 px-4 py-3 rounded-lg bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400 text-white font-semibold text-sm transition-all shadow-lg shadow-purple-900/30"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
            Listen on Lenny's Newsletter
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M7 17L17 7M7 7h10v10" />
            </svg>
          </a>
        </>
      )}
    </div>
  )
}
