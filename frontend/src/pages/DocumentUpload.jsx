import { useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { useI18n } from '../i18n/index.jsx'
import { postDocumentAnalysis, postQA } from '../utils/api.js'
import LoadingDots from '../components/LoadingDots.jsx'
import ErrorBlock from '../components/ErrorBlock.jsx'
import PipelineTrace from '../components/PipelineTrace.jsx'
import ChatThread from '../components/ChatThread.jsx'

const SEVERITY_PILL = {
  high: 'pill-danger',
  medium: 'pill-warning',
  low: 'pill-success',
}

export default function DocumentUpload() {
  const { t, lang } = useI18n()
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [concern, setConcern] = useState('')
  const [drag, setDrag] = useState(false)

  // Initial analysis state
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState(null)
  const [analysis, setAnalysis] = useState(null)

  // Follow-up chat state (post-analysis)
  const [chatMessages, setChatMessages] = useState([])
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState(null)

  const documentText = analysis?.data?._document_text || ''

  const onPick = (f) => {
    if (!f) return
    setFile(f)
    setAnalysisError(null)
    setAnalysis(null)
    setChatMessages([])
    setChatError(null)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDrag(false)
    onPick(e.dataTransfer.files?.[0])
  }

  const analyze = async () => {
    if (!file || analyzing) return
    setAnalyzing(true)
    setAnalysisError(null)
    setAnalysis(null)
    setChatMessages([])
    try {
      const data = await postDocumentAnalysis({ file, concern, language: lang })
      setAnalysis(data)
    } catch (err) {
      setAnalysisError(err.message)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleFollowup = async (text) => {
    const userMsg = { id: Date.now(), role: 'user', content: text }
    const next = [...chatMessages, userMsg]
    setChatMessages(next)
    setChatLoading(true)
    setChatError(null)

    const history = next
      .filter((m) => m.role === 'user' || (m.role === 'assistant' && m.content))
      .map((m) => ({ role: m.role, content: m.content }))
      .slice(0, -1)

    try {
      const data = await postQA({
        query: text,
        language: lang,
        history,
        documentContext: documentText,
      })
      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.data?.answer || '(no answer)',
        response: data,
      }
      setChatMessages([...next, assistantMsg])
    } catch (err) {
      setChatError(err.message)
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div>
      <header className="mb-8">
        <h1 className="heading-display text-4xl text-zinc-100">{t('analyze.title')}</h1>
        <p className="mt-2 max-w-3xl text-zinc-400">{t('analyze.subtitle')}</p>
      </header>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDrag(true)
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`card cursor-pointer p-10 text-center transition-colors ${
          drag ? 'border-gold-500/50 bg-gold-500/5' : ''
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.md,.jpg,.jpeg,.png"
          className="hidden"
          onChange={(e) => onPick(e.target.files?.[0])}
        />
        <p className="font-serif text-xl text-zinc-100">{t('analyze.drop')}</p>
        <p className="mt-2 text-xs text-zinc-500">{t('analyze.supports')}</p>
        {file && (
          <p className="mt-4 inline-flex items-center gap-2 rounded-md border border-gold-500/30 bg-gold-500/5 px-3 py-1.5 text-sm text-gold-400">
            {file.name}{' '}
            <span className="text-zinc-500">· {(file.size / 1024).toFixed(0)} KB</span>
          </p>
        )}
      </div>

      <div className="card mt-5 p-5">
        <label className="label">{t('analyze.concern_label')}</label>
        <textarea
          className="input min-h-[80px] resize-y"
          placeholder={t('analyze.concern_placeholder')}
          value={concern}
          onChange={(e) => setConcern(e.target.value)}
        />
        <div className="mt-4 flex justify-end">
          <button
            onClick={analyze}
            disabled={!file || analyzing}
            className="btn-primary"
          >
            {analyzing ? '…' : t('common.analyze')}
          </button>
        </div>
      </div>

      {analyzing && <LoadingDots label={t('common.loading')} />}

      {analysisError && (
        <div className="mt-6">
          <ErrorBlock error={analysisError} onRetry={analyze} />
        </div>
      )}

      {analysis && <AnalysisResult response={analysis} />}

      {analysis && documentText && (
        <section className="mt-12">
          <h2 className="heading-display mb-2 text-2xl text-zinc-100">
            {t('analyze.followup_title')}
          </h2>
          <p className="mb-5 text-sm text-zinc-400">
            The full document text is preserved in this session — your questions
            are answered using its contents plus retrieved Indian law.
          </p>
          <ChatThread
            messages={chatMessages}
            onSubmit={handleFollowup}
            loading={chatLoading}
            error={chatError}
            placeholder={t('analyze.followup_placeholder')}
          />
        </section>
      )}
    </div>
  )
}

function AnalysisResult({ response }) {
  const { t } = useI18n()
  const data = response.data || {}
  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="mt-8 space-y-6"
    >
      <div className="card p-6">
        <div className="mb-2 flex items-center gap-2">
          <span className="pill-gold uppercase">{data.document_type || 'Document'}</span>
        </div>
        <h2 className="heading-display text-2xl text-zinc-100">{t('analyze.summary')}</h2>
        <p className="mt-3 whitespace-pre-line leading-relaxed text-zinc-300">
          {data.summary}
        </p>
      </div>

      {Array.isArray(data.key_clauses) && data.key_clauses.length > 0 && (
        <div className="card p-6">
          <div className="mb-4 flex items-baseline justify-between">
            <h3 className="heading-display text-xl text-zinc-100">
              {t('analyze.key_clauses')}
            </h3>
            <span className="text-xs text-zinc-500">
              {data.key_clauses.length} clauses
            </span>
          </div>
          <ul className="space-y-3">
            {data.key_clauses.map((c, i) => (
              <li key={i} className="rounded-lg border border-white/5 bg-ink-700/40 p-4">
                <p className="text-sm font-semibold text-zinc-100">
                  {i + 1}. {c.clause_title}
                </p>
                {c.clause_text && (
                  <p className="mt-1 font-mono text-xs text-zinc-400 line-clamp-4">
                    "{c.clause_text}"
                  </p>
                )}
                <p className="mt-2 text-sm text-zinc-300">{c.interpretation}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {Array.isArray(data.risks) && data.risks.length > 0 && (
        <div className="card p-6">
          <div className="mb-4 flex items-baseline justify-between">
            <h3 className="heading-display text-xl text-zinc-100">
              {t('analyze.risks')}
            </h3>
            <span className="text-xs text-zinc-500">
              {data.risks.length} risks identified
            </span>
          </div>
          <ul className="space-y-3">
            {data.risks.map((r, i) => (
              <li key={i} className="rounded-lg border border-white/5 bg-ink-700/40 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <span className={SEVERITY_PILL[r.severity] || 'pill-zinc'}>
                    {r.severity}
                  </span>
                  <span className="text-sm font-semibold text-zinc-100">
                    {i + 1}. {r.issue}
                  </span>
                </div>
                <p className="text-sm text-zinc-300">{r.explanation}</p>
                {typeof r.supporting_law_cite === 'number' && (
                  <span className="pill-zinc mt-2 inline-flex">
                    [#{r.supporting_law_cite}]
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {Array.isArray(data.recommendations) && data.recommendations.length > 0 && (
        <div className="card p-6">
          <h3 className="heading-display mb-3 text-xl text-zinc-100">
            {t('analyze.recommendations')}
          </h3>
          <ul className="space-y-1.5 text-sm text-zinc-300">
            {data.recommendations.map((r, i) => (
              <li key={i} className="flex gap-2">
                <span className="mt-1 block h-1.5 w-1.5 rounded-full bg-gold-500 flex-shrink-0" />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <PipelineTrace trace={response.pipeline_trace} />
    </motion.section>
  )
}
