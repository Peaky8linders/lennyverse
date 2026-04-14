import { memo } from 'react'

interface Props {
  domain: string
  size?: number
  className?: string
}

/**
 * Inline SVG icon per category. Keyed by lowercased domain label so it tolerates
 * "Product Strategy" / "product strategy" / "product-strategy" variants.
 */
function DomainIconInner({ domain, size = 18, className }: Props) {
  const key = (domain || '').toLowerCase().trim()
  const common = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    className,
  }

  if (key.includes('career')) {
    // briefcase
    return (
      <svg {...common}>
        <rect x="3" y="7" width="18" height="13" rx="2" />
        <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        <path d="M3 13h18" />
      </svg>
    )
  }
  if (key.includes('design')) {
    // palette
    return (
      <svg {...common}>
        <circle cx="13" cy="12" r="9" />
        <circle cx="8" cy="9" r="1.2" fill="currentColor" stroke="none" />
        <circle cx="7" cy="14" r="1.2" fill="currentColor" stroke="none" />
        <circle cx="11" cy="17" r="1.2" fill="currentColor" stroke="none" />
        <circle cx="17" cy="8" r="1.2" fill="currentColor" stroke="none" />
        <path d="M13 21a3 3 0 0 0 3-3c0-1.5-1-2-1-3s1-1.5 2-1.5h1" />
      </svg>
    )
  }
  if (key.includes('engineering')) {
    // cpu
    return (
      <svg {...common}>
        <rect x="5" y="5" width="14" height="14" rx="2" />
        <rect x="9" y="9" width="6" height="6" rx="1" />
        <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
      </svg>
    )
  }
  if (key.includes('growth')) {
    // trending up
    return (
      <svg {...common}>
        <path d="M3 17l6-6 4 4 8-8" />
        <path d="M14 7h7v7" />
      </svg>
    )
  }
  if (key.includes('leadership')) {
    // crown
    return (
      <svg {...common}>
        <path d="M3 7l4 5 5-7 5 7 4-5v11H3z" />
        <path d="M3 21h18" />
      </svg>
    )
  }
  if (key.includes('product') || key.includes('strategy')) {
    // target
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="9" />
        <circle cx="12" cy="12" r="5" />
        <circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" />
      </svg>
    )
  }
  // uncategorized / fallback — sparkles
  return (
    <svg {...common}>
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6" />
    </svg>
  )
}

export default memo(DomainIconInner)
