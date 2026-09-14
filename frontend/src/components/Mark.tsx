/** The Truth Trace mark: two nested squares, rotated — one account inside the other. */
export function Mark({ size = 22 }: { size?: number }) {
  return (
    <span
      aria-hidden
      style={{ width: size, height: size, transform: 'rotate(45deg)' }}
      className="relative block flex-none"
    >
      <span className="absolute inset-0 border-2 border-[var(--color-accent)]" />
      <span
        className="absolute border-2 border-[var(--color-danger)]"
        style={{ inset: Math.round(size * 0.23) }}
      />
    </span>
  )
}

/** Initials bubble used wherever a person is named. */
export function Avatar({ name, tone = 'accent' }: { name: string; tone?: 'accent' | 'violet' }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')

  const color = tone === 'violet' ? 'var(--color-violet)' : 'var(--color-accent)'
  return (
    <span
      className="tt-mono flex h-8 w-8 flex-none items-center justify-center rounded-full text-[11px] font-bold"
      style={{ background: `color-mix(in srgb, ${color} 16%, transparent)`, color }}
    >
      {initials}
    </span>
  )
}
