import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useI18n } from '../i18n/index.jsx'
import CitationCard from './CitationCard.jsx'
import ErrorBlock from './ErrorBlock.jsx'
import PipelineTrace from './PipelineTrace.jsx'

/**
 * Shared conversational chat UI used by:
 *   - Legal Q&A
 *   - Case Strategy
 *   - Document Analyzer follow-up panel
 *
 * Behaviour:
 *   - The FIRST assistant message in the thread renders a full structured
 *     details panel (provisions / phases / citations / pipeline trace).
 *   - Subsequent assistant messages (follow-ups) render as a concise chat
 *     bubble with optional inline citation chips. No detail panel.
 *
 * Props:
 *   messages         — array of { id, role: 'user' | 'assistant', content, response? }
 *   onSubmit         — async (text: string) => void
 *   loading          — boolean
 *   error            — string | null
 *   placeholder      — input placeholder for the first message
 *   suggestions      — string[]: clickable example prompts shown before the
 *                      first message. Clicking sends the suggestion as the
 *                      first user message.
 *   renderFirstDetails(response) → ReactNode | null
 *                      Customises the details panel under the first assistant
 *                      message. Defaults to QA-style details (provisions,
 *                      recommended actions, citations).
 */
export default function ChatThread({
  messages,
  onSubmit,
  loading,
  error,
  placeholder,
  suggestions = [],
  renderFirstDetails,
}) {
  const { t } = useI18n()
  const [draft, setDraft] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  const submit = async (e) => {
    e.preventDefault()
    const text = draft.trim()
    if (!text || loading) return
    setDraft('')
    await onSubmit(text)
  }

  const hasHistory = messages.length > 0
  const firstAssistantIndex = messages.findIndex((m) => m.role === 'assistant')

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit(e)
    }
  }

  const showSuggestions = !hasHistory && !loading && suggestions.length > 0

  return (
    <div className="space-y-4">
      {showSuggestions && (
        <SuggestionPanel
          suggestions={suggestions}
          onPick={(text) => onSubmit(text)}
        />
      )}

      <AnimatePresence initial={false}>
        {messages.map((m, idx) => {
          if (m.role === 'user') {
            return <UserBubble key={m.id} text={m.content} />
          }
          const isFirstAssistant = idx === firstAssistantIndex
          return (
            <AssistantBubble
              key={m.id}
              text={m.content}
              response={m.response}
              detailsNode={
                isFirstAssistant && m.response
                  ? (renderFirstDetails
                      ? renderFirstDetails(m.response)
                      : <QAResponseDetails response={m.response} />)
                  : null
              }
              inlineCitations={!isFirstAssistant ? m.response?.citations : null}
            />
          )
        })}
      </AnimatePresence>

      {loading && <ThinkingBubble label={t('common.loading')} />}

      <ErrorBlock error={error} />

      <div ref={bottomRef} />

      <form onSubmit={submit} className="card p-4">
        <textarea
          className="input min-h-[72px] resize-y"
          placeholder={hasHistory ? t('common.followup_placeholder') : placeholder}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={loading}
        />
        <div className="mt-3 flex items-center justify-between">
          <p className="text-xs text-zinc-500">{draft.length}/2000</p>
          <button
            type="submit"
            disabled={loading || !draft.trim()}
            className="btn-primary"
          >
            {loading ? '…' : hasHistory ? t('common.send') : t('common.ask')}
          </button>
        </div>
      </form>
    </div>
  )
}

function UserBubble({ text }) {
  const { t } = useI18n()
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex justify-end"
    >
      <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-gold-500/15 border border-gold-500/30 px-4 py-3">
        <p className="mb-1 text-[10px] uppercase tracking-wider text-gold-400">
          {t('common.you')}
        </p>
        <p className="whitespace-pre-wrap text-sm text-zinc-100 leading-relaxed">
          {text}
        </p>
      </div>
    </motion.div>
  )
}

function AssistantBubble({ text, response, detailsNode, inlineCitations }) {
  const { t } = useI18n()
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard API not available — silent no-op */
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-3"
    >
      <div className="group relative max-w-[92%] rounded-2xl rounded-tl-sm bg-ink-700/60 border border-white/5 px-4 py-3">
        <div className="mb-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] uppercase tracking-wider text-zinc-500">
          <span>{t('common.assistant')}</span>
          {response?.pipeline_trace?.classification?.domain && (
            <span className="text-gold-400">
              · {response.pipeline_trace.classification.domain}
            </span>
          )}
          {response?.pipeline_trace?.model && (
            <span
              className="text-zinc-600 font-mono normal-case tracking-normal"
              title={t('common.model_label')}
            >
              · {response.pipeline_trace.model}
            </span>
          )}
          <button
            type="button"
            onClick={handleCopy}
            aria-label={copied ? t('common.copied') : t('common.copy')}
            className={`ml-auto rounded px-1.5 py-0.5 text-[10px] font-medium tracking-wider transition-colors ${
              copied
                ? 'text-accent-success'
                : 'text-zinc-500 opacity-0 hover:text-zinc-200 group-hover:opacity-100 focus:opacity-100'
            }`}
          >
            {copied ? `✓ ${t('common.copied')}` : t('common.copy')}
          </button>
        </div>
        <p className="whitespace-pre-wrap text-sm text-zinc-100 leading-relaxed">
          {text}
        </p>
        {Array.isArray(inlineCitations) && inlineCitations.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {inlineCitations.map((c) => (
              <span
                key={c.cite}
                className="pill-gold font-mono text-[10px]"
                title={c.snippet}
              >
                {c.act_name} § {c.section}
              </span>
            ))}
          </div>
        )}
      </div>
      {detailsNode}
    </motion.div>
  )
}

function SuggestionPanel({ suggestions, onPick }) {
  const { t } = useI18n()
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-5"
    >
      <p className="mb-3 text-xs uppercase tracking-wider text-zinc-500">
        {t('common.try_asking')}
      </p>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((s, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onPick(s)}
            className="rounded-lg border border-white/10 bg-ink-700/40 px-3 py-2 text-left text-sm text-zinc-300 transition-colors hover:border-gold-500/40 hover:bg-gold-500/5 hover:text-zinc-100"
          >
            {s}
          </button>
        ))}
      </div>
    </motion.div>
  )
}

function ThinkingBubble({ label }) {
  return (
    <div className="flex items-center gap-2 px-1">
      <div className="flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="block h-1.5 w-1.5 rounded-full bg-gold-500"
            animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
            transition={{ duration: 1.2, delay: i * 0.18, repeat: Infinity }}
          />
        ))}
      </div>
      <span className="text-xs text-zinc-500">{label}</span>
    </div>
  )
}

/* ------------------- Default details panel (QA-style) ------------------- */

function QAResponseDetails({ response }) {
  const { t } = useI18n()
  const data = response.data || {}
  return (
    <div className="space-y-4 pl-2">
      {Array.isArray(data.key_provisions) && data.key_provisions.length > 0 && (
        <div className="card p-5">
          <h3 className="heading-display mb-3 text-lg text-zinc-100">
            {t('chat.key_provisions')}
          </h3>
          <ul className="space-y-2.5">
            {data.key_provisions.map((p, i) => (
              <li
                key={i}
                className="rounded-lg border border-white/5 bg-ink-700/40 p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-gold-400">
                    {p.act_name} § {p.section}
                  </span>
                  {typeof p.cite === 'number' && (
                    <span className="pill-zinc">[#{p.cite}]</span>
                  )}
                </div>
                <p className="mt-1.5 text-sm text-zinc-300">{p.summary}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {Array.isArray(data.recommended_actions) &&
        data.recommended_actions.length > 0 && (
          <div className="card p-5">
            <h3 className="heading-display mb-3 text-lg text-zinc-100">
              {t('chat.recommended_actions')}
            </h3>
            <ol className="space-y-2 text-sm text-zinc-300">
              {data.recommended_actions.map((s, i) => (
                <li key={i} className="flex gap-3">
                  <span className="font-mono text-gold-400 w-6 flex-shrink-0">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <span>{s}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

      {Array.isArray(response.citations) && response.citations.length > 0 && (
        <div>
          <h3 className="heading-display mb-2 text-lg text-zinc-100">Citations</h3>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {response.citations.map((c) => (
              <CitationCard key={c.cite} citation={c} />
            ))}
          </div>
        </div>
      )}

      {Array.isArray(data.warnings) && data.warnings.length > 0 && (
        <div className="card border-accent-warning/30 bg-accent-warning/5 p-4">
          <h3 className="heading-display mb-1.5 text-sm text-accent-warning">
            {t('chat.warnings')}
          </h3>
          <ul className="space-y-1 text-xs text-zinc-300">
            {data.warnings.map((w, i) => (
              <li key={i}>• {w}</li>
            ))}
          </ul>
        </div>
      )}

      <PipelineTrace trace={response.pipeline_trace} />
    </div>
  )
}
