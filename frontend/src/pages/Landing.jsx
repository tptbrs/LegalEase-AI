import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useI18n } from '../i18n/index.jsx'

const featureList = [
  { key: 'qa', to: '/chat', icon: QAIcon },
  { key: 'strategy', to: '/strategy', icon: StrategyIcon },
  { key: 'fir', to: '/fir', icon: FIRIcon },
  { key: 'analyze', to: '/analyze', icon: AnalyzeIcon },
  { key: 'pipeline', to: '/chat', icon: PipelineIcon },
]

export default function Landing() {
  const { t } = useI18n()
  return (
    <div className="space-y-20">
      <section className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12">
        <motion.div
          className="lg:col-span-7"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <span className="pill-gold uppercase">{t('landing.tagline')}</span>
          <h1 className="heading-display mt-5 text-5xl font-semibold leading-tight text-zinc-100 md:text-6xl">
            {t('landing.title')}
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-zinc-400">
            {t('landing.subtitle')}
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/chat" className="btn-primary">
              {t('landing.cta_primary')}
            </Link>
            <Link to="/strategy" className="btn-outline-gold">
              {t('landing.cta_secondary')}
            </Link>
          </div>
        </motion.div>

        <motion.div
          className="lg:col-span-5"
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <PipelineDiagram />
        </motion.div>
      </section>

      <section>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {featureList.map((f, i) => (
            <motion.div
              key={f.key}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: i * 0.06 }}
            >
              <Link to={f.to} className="card card-hover block p-6 h-full">
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-gold-500/10 ring-1 ring-gold-500/30">
                  <f.icon />
                </div>
                <h3 className="font-serif text-xl text-zinc-100">
                  {t(`landing.feature_${f.key}_title`)}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-zinc-400">
                  {t(`landing.feature_${f.key}_body`)}
                </p>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  )
}

function PipelineDiagram() {
  const stages = [
    'classify',
    'embed',
    'retrieve',
    'rerank',
    'prompt',
    'gemini',
    'parse',
  ]
  return (
    <div className="card relative overflow-hidden p-6">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(212,175,55,0.10),transparent_60%)]" />
      <div className="relative">
        <p className="font-mono text-[10px] uppercase tracking-widest text-gold-500">
          rag pipeline
        </p>
        <div className="mt-4 space-y-2">
          {stages.map((s, i) => (
            <motion.div
              key={s}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 + i * 0.08 }}
              className="flex items-center gap-3 rounded-lg border border-white/5 bg-ink-700/40 px-3 py-2"
            >
              <span className="font-mono text-xs text-zinc-500 w-5 text-right">
                {String(i + 1).padStart(2, '0')}
              </span>
              <span className="block h-1 w-1 rounded-full bg-gold-500" />
              <span className="font-mono text-sm text-zinc-200">{s}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}

function QAIcon() {
  return (
    <svg className="h-5 w-5 text-gold-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <path d="M21 12a9 9 0 1 1-3.5-7.1L21 3v7h-7" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  )
}
function FIRIcon() {
  return (
    <svg className="h-5 w-5 text-gold-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
      <path d="M14 3v6h6" />
      <path d="M9 14h6M9 17h4" />
    </svg>
  )
}
function AnalyzeIcon() {
  return (
    <svg className="h-5 w-5 text-gold-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
      <path d="M11 8v6M8 11h6" />
    </svg>
  )
}
function PipelineIcon() {
  return (
    <svg className="h-5 w-5 text-gold-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
      <path d="M10 6.5h4M6.5 10v4M14 17.5h-4M17.5 10v4" />
    </svg>
  )
}
function StrategyIcon() {
  return (
    <svg className="h-5 w-5 text-gold-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <path d="M4 6h6M4 12h10M4 18h14" />
      <circle cx="14" cy="6" r="1.5" />
      <circle cx="18" cy="12" r="1.5" />
    </svg>
  )
}
