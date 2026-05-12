import { useState } from 'react'
import { useI18n } from '../i18n/index.jsx'
import { postStrategy } from '../utils/api.js'
import ChatThread from '../components/ChatThread.jsx'
import CitationCard from '../components/CitationCard.jsx'
import PipelineTrace from '../components/PipelineTrace.jsx'

const SUGGESTIONS_EN = [
  "My tenant has stopped paying rent for the last 3 months. What should I do?",
  "An e-commerce site sold me a defective product and refuses to refund.",
  "My employer terminated me without notice or severance. What recourse do I have?",
  "A neighbour has encroached on my property boundary. How do I respond legally?",
]

const SUGGESTIONS_HI = [
  "किरायेदार ने 3 महीने से किराया नहीं दिया है। क्या करूँ?",
  "ई-कॉमर्स साइट ने खराब उत्पाद बेचा और रिफंड से इनकार।",
  "नियोक्ता ने बिना नोटिस के नौकरी से निकाला। क्या उपाय है?",
  "पड़ोसी ने संपत्ति की सीमा पर अतिक्रमण किया है। कानूनी जवाब कैसे दें?",
]

export default function Strategy() {
  const { t, lang } = useI18n()
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (text) => {
    const userMsg = { id: Date.now(), role: 'user', content: text }
    const next = [...messages, userMsg]
    setMessages(next)
    setLoading(true)
    setError(null)

    const history = next
      .filter((m) => m.role === 'user' || (m.role === 'assistant' && m.content))
      .map((m) => ({ role: m.role, content: m.content }))
      .slice(0, -1)

    try {
      const data = await postStrategy({ query: text, language: lang, history })
      // First-turn answer = the strategy overview; follow-up answer = answer field.
      const answerText =
        data.data?.overview ||
        data.data?.answer ||
        '(see plan below)'
      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: answerText,
        response: data,
      }
      setMessages([...next, assistantMsg])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setMessages([])
    setError(null)
  }

  return (
    <div>
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="heading-display text-4xl text-zinc-100">{t('strategy.title')}</h1>
          <p className="mt-2 max-w-3xl text-zinc-400">{t('strategy.subtitle')}</p>
        </div>
        {messages.length > 0 && (
          <button onClick={reset} className="btn-ghost text-xs">
            {t('common.new_chat')}
          </button>
        )}
      </header>

      <ChatThread
        messages={messages}
        onSubmit={handleSubmit}
        loading={loading}
        error={error}
        placeholder={t('strategy.placeholder')}
        suggestions={lang === 'hi' ? SUGGESTIONS_HI : SUGGESTIONS_EN}
        renderFirstDetails={(response) => <StrategyPlanDetails response={response} />}
      />
    </div>
  )
}

const COST_PILL = {
  minimal: 'pill-success',
  low: 'pill-success',
  medium: 'pill-warning',
  moderate: 'pill-warning',
  high: 'pill-danger',
}

function StrategyPlanDetails({ response }) {
  const { t } = useI18n()
  const data = response.data || {}
  const phases = Array.isArray(data.phases) ? data.phases : []

  // If the response shape is not STRATEGY (e.g. fallback to chat), don't render.
  if (phases.length === 0) return null

  return (
    <div className="space-y-5 pl-2">
      {data.domain && (
        <div className="flex items-center gap-2">
          <span className="pill-gold uppercase">{t('strategy.domain')}</span>
          <span className="text-sm text-zinc-300">{data.domain}</span>
        </div>
      )}

      <div className="card p-5">
        <div className="mb-4 flex items-baseline justify-between">
          <h3 className="heading-display text-lg text-zinc-100">
            {t('strategy.phases_title')}
          </h3>
          <span className="text-xs text-zinc-500">{phases.length} phases</span>
        </div>
        <ol className="space-y-4">
          {phases.map((p, i) => {
            const costKey = String(p.estimated_cost || '').toLowerCase()
            const costClass =
              Object.keys(COST_PILL).find((k) => costKey.includes(k))
            return (
              <li
                key={i}
                className="relative rounded-lg border border-white/5 bg-ink-700/40 p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gold-500/15 text-sm font-mono text-gold-400 ring-1 ring-gold-500/40">
                      {p.phase_number ?? i + 1}
                    </span>
                    <h4 className="font-serif text-base text-zinc-100">
                      {p.title}
                    </h4>
                  </div>
                  <div className="flex gap-1.5">
                    {p.expected_duration && (
                      <span className="pill-zinc">{p.expected_duration}</span>
                    )}
                    {p.estimated_cost && (
                      <span
                        className={
                          costClass ? COST_PILL[costClass] : 'pill-zinc'
                        }
                      >
                        {p.estimated_cost}
                      </span>
                    )}
                  </div>
                </div>
                <p className="mt-2 text-sm text-zinc-300">{p.description}</p>
                {Array.isArray(p.statutory_basis) && p.statutory_basis.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {p.statutory_basis.map((b, j) => (
                      <span key={j} className="pill-gold font-mono text-[10px]">
                        {b.act_name} § {b.section}
                      </span>
                    ))}
                  </div>
                )}
                {p.risks_if_skipped && (
                  <p className="mt-2 text-xs text-accent-warning">
                    Risk if skipped: {p.risks_if_skipped}
                  </p>
                )}
              </li>
            )
          })}
        </ol>
      </div>

      {Array.isArray(data.critical_deadlines) &&
        data.critical_deadlines.length > 0 && (
          <div className="card border-accent-warning/30 bg-accent-warning/5 p-4">
            <h3 className="heading-display mb-2 text-sm text-accent-warning">
              {t('strategy.deadlines_title')}
            </h3>
            <ul className="space-y-1 text-sm text-zinc-300">
              {data.critical_deadlines.map((d, i) => (
                <li key={i}>• {d}</li>
              ))}
            </ul>
          </div>
        )}

      {Array.isArray(data.evidence_to_preserve) &&
        data.evidence_to_preserve.length > 0 && (
          <div className="card p-4">
            <h3 className="heading-display mb-2 text-sm text-zinc-100">
              {t('strategy.evidence_title')}
            </h3>
            <ul className="space-y-1 text-sm text-zinc-300">
              {data.evidence_to_preserve.map((e, i) => (
                <li key={i}>• {e}</li>
              ))}
            </ul>
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
