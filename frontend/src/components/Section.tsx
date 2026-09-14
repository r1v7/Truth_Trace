import type { ReactNode } from 'react'

/** A titled panel. Every major block on a case page is one of these, so the page
 *  reads as a sequence of steps rather than a wall of controls. */
export function Section({
  title,
  aside,
  children,
}: {
  title: string
  aside?: string
  children: ReactNode
}) {
  return (
    <section className="tt-card tt-rise overflow-hidden">
      <header className="flex flex-wrap items-center gap-3 border-b border-[var(--color-line)] px-5 py-3.5">
        <h2 className="tt-label m-0 text-[var(--color-accent)]">{title}</h2>
        {aside && (
          <span className="ms-auto text-[12px] text-[var(--color-muted-dim)]">{aside}</span>
        )}
      </header>
      <div className="p-5">{children}</div>
    </section>
  )
}
