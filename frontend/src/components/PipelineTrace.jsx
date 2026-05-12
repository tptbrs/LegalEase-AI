import { useState } from 'react'
import { motion } from 'framer-motion'
import { useI18n } from '../i18n/index.jsx'

export default function PipelineTrace({ trace }) {
  const { t } = useI18n()
  // Collapsed by default — examiners and users click to expand when they
  // want the X-ray view. Keeps the answer area clean.
  const [open, setOpen] = useState(false)

  if (!trace) return null

  const totalLatency =
    trace.latency_ms && Object.values(trace.latency_ms).reduce((a, b) => a + b, 0)

  return (
    <section className="card mt-8 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <span className="block h-2 w-2 rounded-full bg-gold-500 animate-pulse-slow" />
          <h3 className="font-serif text-lg text-zinc-100">{t('pipeline.title')}</h3>
          <span className="pill-zinc">{trace.prompt_mode}</span>
          <span className="pill-zinc font-mono">{trace.model}</span>
        </div>
        <span className="text-xs text-zinc-400">
          {totalLatency ? `${totalLatency.toFixed(0)} ms · ` : ''}
          {open ? '▲' : '▼'}
        </span>
      </button>

      {open && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          transition={{ duration: 0.2 }}
          className="border-t border-white/5"
        >
          <div className="grid grid-cols-1 gap-4 p-5 lg:grid-cols-3">
            <Block title={t('pipeline.classification')}>
              <div className="space-y-1.5 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-zinc-400">domain</span>
                  <span className="pill-gold uppercase">
                    {trace.classification.domain}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-zinc-400">confidence</span>
                  <span className="font-mono text-zinc-200">
                    {(trace.classification.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                {trace.classification.matched_keywords?.length > 0 && (
                  <div>
                    <p className="mt-2 text-xs uppercase tracking-wider text-zinc-500">
                      {t('pipeline.matched_keywords')}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {trace.classification.matched_keywords
                        .slice(0, 12)
                        .map((kw) => (
                          <span key={kw} className="pill-zinc text-[10px]">
                            {kw}
                          </span>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            </Block>

            <Block title={`${t('pipeline.retrieved')} (${trace.retrieved_chunks?.length || 0})`}>
              <ul className="max-h-64 space-y-2 overflow-y-auto pr-1 text-xs">
                {trace.retrieved_chunks?.slice(0, 10).map((c) => (
                  <li
                    key={c.chunk_id}
                    className="rounded-md border border-white/5 bg-ink-700/40 p-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-zinc-500 truncate max-w-[60%]">
                        {c.metadata?.section
                          ? `§ ${c.metadata.section}`
                          : c.chunk_id}
                      </span>
                      <span className="pill-zinc font-mono text-[10px]">
                        sim {c.similarity}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-zinc-400">{c.preview}</p>
                  </li>
                ))}
              </ul>
            </Block>

            <Block title={`${t('pipeline.reranked')} (${trace.reranked_chunks?.length || 0})`}>
              <ul className="max-h-64 space-y-2 overflow-y-auto pr-1 text-xs">
                {trace.reranked_chunks?.map((c, i) => (
                  <li
                    key={c.chunk_id}
                    className="rounded-md border border-gold-500/15 bg-gold-500/5 p-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-gold-400">[#{i + 1}]</span>
                      <span className="font-mono text-[10px] text-zinc-300">
                        rerank {c.rerank_score.toFixed(3)}
                      </span>
                    </div>
                    <p className="mt-1 truncate font-mono text-[10px] text-zinc-400">
                      {c.metadata?.act_name} § {c.metadata?.section}
                    </p>
                  </li>
                ))}
              </ul>
            </Block>
          </div>

          {trace.latency_ms && (
            <div className="border-t border-white/5 px-5 py-3">
              <p className="mb-1.5 text-xs uppercase tracking-wider text-zinc-500">
                {t('pipeline.latency')}
              </p>
              <div className="flex flex-wrap gap-2 text-xs font-mono">
                {Object.entries(trace.latency_ms).map(([k, v]) => (
                  <span key={k} className="pill-zinc">
                    {k.replace('_ms', '')} · {v.toFixed(1)}ms
                  </span>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </section>
  )
}

function Block({ title, children }) {
  return (
    <div className="rounded-lg border border-white/5 bg-ink-700/30 p-4">
      <h4 className="mb-3 text-xs uppercase tracking-wider text-zinc-400">{title}</h4>
      {children}
    </div>
  )
}
