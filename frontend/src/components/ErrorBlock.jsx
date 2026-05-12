import { useI18n } from '../i18n/index.jsx'

const NETWORK_ERROR_PATTERNS = [
  /network error/i,
  /econnrefused/i,
  /failed to fetch/i,
  /err_network/i,
  /backend unreachable/i,
]

function isNetworkError(message) {
  if (!message) return false
  return NETWORK_ERROR_PATTERNS.some((p) => p.test(message))
}

/**
 * Unified error display. Distinguishes between network-level failures
 * (backend down) and application-level errors (validation, LLM, etc.) so
 * the user sees a useful next step instead of a raw axios message.
 *
 * Props:
 *   error    — string (the error message) or null
 *   onRetry  — optional callback; if provided, a "Try again" button is shown
 */
export default function ErrorBlock({ error, onRetry }) {
  const { t } = useI18n()
  if (!error) return null

  if (isNetworkError(error)) {
    return (
      <div className="card border-accent-warning/30 bg-accent-warning/5 p-5">
        <div className="flex items-start gap-3">
          <span
            aria-hidden
            className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-warning/15 text-accent-warning"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
            >
              <path d="M12 9v4" />
              <path d="M12 17h.01" />
              <circle cx="12" cy="12" r="9" />
            </svg>
          </span>
          <div className="flex-1">
            <p className="font-semibold text-zinc-100">
              {t('errors.backend_down_title')}
            </p>
            <p className="mt-1 text-sm text-zinc-300">
              {t('errors.backend_down_body')}
            </p>
            <p className="mt-2 font-mono text-xs text-zinc-500">
              python main.py
            </p>
            {onRetry && (
              <button onClick={onRetry} className="btn-outline-gold mt-3">
                {t('errors.try_again')}
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card border-accent-danger/30 bg-accent-danger/5 p-4">
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-danger/15 text-accent-danger"
        >
          <svg
            viewBox="0 0 24 24"
            className="h-3.5 w-3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
          >
            <path d="M6 6l12 12" />
            <path d="M6 18L18 6" />
          </svg>
        </span>
        <div className="flex-1">
          <p className="text-sm font-medium text-accent-danger">
            {t('common.error')}
          </p>
          <p className="mt-0.5 text-sm text-zinc-300">{error}</p>
          {onRetry && (
            <button onClick={onRetry} className="btn-ghost mt-3 text-xs">
              {t('errors.try_again')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
