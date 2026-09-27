import { cn } from '@/lib/utils'

export const PRODUCT_NAME = 'SkillBridge'

/**
 * The SkillBridge "Keystone" mark (docs/design/skillbridge-design/pages/Logos.dc.html, option 2):
 * a terracotta arch of blocks, an amber keystone and an ink base line. `tone="dark"` is the
 * version for dark surfaces (lighter arch, white base).
 */
export function LogoMark({
  size = 38,
  tone = 'light',
  className,
  title = `${PRODUCT_NAME} logo`,
}: {
  size?: number
  tone?: 'light' | 'dark'
  className?: string
  /** Accessible name; pass an empty string when the wordmark next to it names the product. */
  title?: string
}) {
  const arch = tone === 'dark' ? '#E8764A' : '#A8431E'
  const base = tone === 'dark' ? '#FFFFFF' : '#231A14'
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      className={cn('shrink-0', className)}
      role={title ? 'img' : undefined}
      aria-label={title || undefined}
      aria-hidden={title ? undefined : true}
    >
      <path d="M12 46A20 20 0 0 1 52 46" stroke={arch} strokeWidth="9" strokeDasharray="10.6 2.4" />
      <path d="M27.5 18.5H36.5L35 31H29Z" fill="#F2B84B" />
      <path d="M7 51H57" stroke={base} strokeWidth="4" strokeLinecap="round" />
    </svg>
  )
}

/** Mark + "SkillBridge" wordmark, with an optional line underneath (e.g. the department). */
export function Logo({
  size = 38,
  tone = 'light',
  subtitle,
  className,
}: {
  size?: number
  tone?: 'light' | 'dark'
  subtitle?: string
  className?: string
}) {
  return (
    <span className={cn('flex items-center gap-2.5', className)}>
      <LogoMark size={size} tone={tone} title="" />
      <span className="flex min-w-0 flex-col">
        <span
          className={cn(
            'font-extrabold tracking-[-0.02em]',
            tone === 'dark' ? 'text-white' : 'text-ink',
          )}
          style={{ fontSize: Math.round(size * 0.47) }}
        >
          {PRODUCT_NAME}
        </span>
        {subtitle && (
          <span className={cn('text-[11px]', tone === 'dark' ? 'text-white/70' : 'text-muted-ink')}>
            {subtitle}
          </span>
        )}
      </span>
    </span>
  )
}
