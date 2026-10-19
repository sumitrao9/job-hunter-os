import { useEffect, useRef, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'

interface DetailDrawerProps {
  open: boolean
  onClose: () => void
  title: ReactNode
  subtitle?: ReactNode
  width?: 'md' | 'lg'
  footer?: ReactNode
  children: ReactNode
}

const WIDTHS = {
  md: 'max-w-md',
  lg: 'max-w-xl',
}

/**
 * Right-side detail panel. Traps focus loosely by moving it inside on open,
 * closes on Escape, and renders nothing when closed so nothing is focusable.
 */
export function DetailDrawer({
  open,
  onClose,
  title,
  subtitle,
  width = 'md',
  footer,
  children,
}: DetailDrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    panelRef.current?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
            aria-hidden="true"
          />
          <motion.div
            ref={panelRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-label={typeof title === 'string' ? title : 'Details'}
            className={`fixed inset-y-0 right-0 z-50 flex w-full ${WIDTHS[width]} flex-col border-l border-line bg-surface-raised shadow-lg outline-none`}
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'tween', duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          >
            <header className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-fg">{title}</div>
                {subtitle && (
                  <div className="mt-0.5 truncate text-xs text-fg-muted">{subtitle}</div>
                )}
              </div>
              <button
                onClick={onClose}
                aria-label="Close details"
                className="shrink-0 rounded-md p-1 text-fg-subtle transition-colors hover:bg-surface-sunken hover:text-fg"
              >
                <X size={16} />
              </button>
            </header>

            <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>

            {footer && (
              <footer className="flex items-center justify-end gap-2 border-t border-line bg-surface-sunken/60 px-5 py-3">
                {footer}
              </footer>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}