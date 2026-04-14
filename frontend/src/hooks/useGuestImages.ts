import { useEffect, useState } from 'react'

/**
 * Loads static JSON maps produced by `scripts/fetch_guest_images.py`:
 *   - /guest_images.json     { "<guest-slug>": "<image_url>" }
 *   - /episode_images.json   { "ep-<title-slug>": "<image_url>" }
 *
 * These are fetched once at mount and cached in module scope so multiple
 * components don't re-download them.
 */

let guestCache: Record<string, string> | null = null
let episodeCache: Record<string, string> | null = null
let inflight: Promise<void> | null = null

async function loadMaps(): Promise<void> {
  if (guestCache && episodeCache) return
  if (inflight) return inflight
  inflight = (async () => {
    try {
      const [gRes, eRes] = await Promise.all([
        fetch('/guest_images.json'),
        fetch('/episode_images.json'),
      ])
      guestCache = gRes.ok ? await gRes.json() : {}
      episodeCache = eRes.ok ? await eRes.json() : {}
    } catch {
      guestCache = {}
      episodeCache = {}
    }
  })()
  return inflight
}

export function useGuestImages() {
  const [ready, setReady] = useState(!!guestCache && !!episodeCache)

  useEffect(() => {
    if (ready) return
    let mounted = true
    loadMaps().then(() => {
      if (mounted) setReady(true)
    })
    return () => {
      mounted = false
    }
  }, [ready])

  return {
    ready,
    getGuestImage: (slug: string): string | undefined => guestCache?.[slug],
    getEpisodeImage: (episodeId: string): string | undefined => episodeCache?.[episodeId],
  }
}
