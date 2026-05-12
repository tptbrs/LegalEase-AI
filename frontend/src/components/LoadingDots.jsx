import { motion } from 'framer-motion'

const stages = [
  'classify',
  'retrieve',
  'rerank',
  'prompt',
  'synthesise',
  'parse',
]

export default function LoadingDots({ label }) {
  return (
    <div className="flex flex-col items-center gap-3 py-8">
      <div className="flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="block h-2 w-2 rounded-full bg-gold-500"
            animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
            transition={{ duration: 1.2, delay: i * 0.18, repeat: Infinity, ease: 'easeInOut' }}
          />
        ))}
      </div>
      <p className="text-sm text-zinc-400">{label}</p>
      <div className="flex flex-wrap items-center justify-center gap-1.5 text-[10px] uppercase tracking-wider text-zinc-500">
        {stages.map((s, i) => (
          <span key={s} className="flex items-center gap-1.5">
            <span className="rounded-full border border-white/10 px-2 py-0.5">{s}</span>
            {i < stages.length - 1 && <span>›</span>}
          </span>
        ))}
      </div>
    </div>
  )
}
