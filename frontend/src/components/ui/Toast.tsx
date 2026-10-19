import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, Info, TriangleAlert, X, AlertCircle } from 'lucide-react'
import { useAppStore, type ToastTone } from '../../store/useAppStore'
import { cx } from '../ui'

const TONE_STYLES: Record<ToastTone, { box: string; icon: React.ReactNode }> = {
  accent: { box: 'border-accent/40 bg-accent-soft', icon: <CheckCircle2 size={15} className="text-accent" /> },
  info: { box: 'border-info/40 bg-info-soft', icon: <Info size={15} className="text-info" /> },
  warn: { box: 'border-warn/40 bg-warn-soft', icon: <TriangleAlert size={15} className="text-warn" /> },
  danger: { box: 'border-danger/40 bg-danger-soft', icon: <AlertCircle size={15} className="text-danger" /> },
}

export function ToastViewport() {
  const toasts = useAppStore((s) => s.toasts)
  const dismiss = useAppStore((s) => s.dismissToast)

  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[min(22rem,calc(100vw-2rem))] flex-col gap-2"
    >
      <AnimatePresence initial={false}>
        {toasts.map((toast) => {
          const tone = TONE_STYLES[toast.tone]
          return (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, y: 12, scale: 0.97 }}
              animate={{ opacity: toast.leaving ? 0 : 1, y: toast.leaving ? 8 : 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.97 }}
              transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
              className={cx(
                'pointer-events-auto flex items-start gap-2.5 rounded-xl border bg-surface-overlay p-3 shadow-lg',
                tone.box,
              )}
            >
              <span className="mt-0.5 shrink-0">{tone.icon}</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium leading-snug text-fg">{toast.title}</p>
                {toast.body && (
                  <p className="mt-0.5 text-xs leading-relaxed text-fg-muted">{toast.body}</p>
                )}
              </div>
              <button
                onClick={() => dismiss(toast.id)}
                aria-label="Dismiss notification"
                className="shrink-0 rounded p-0.5 text-fg-subtle transition-colors hover:text-fg"
              >
                <X size={14} />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}