export default function CitationCard({ citation }) {
  return (
    <div className="card p-4 card-hover">
      <div className="mb-2 flex items-center justify-between">
        <span className="pill-gold">[#{citation.cite}]</span>
        <span className="font-mono text-xs text-zinc-500">
          {citation.source_pdf}
        </span>
      </div>
      <h4 className="font-serif text-base text-zinc-100">
        {citation.act_name}
        {citation.year ? <span className="text-zinc-500"> · {citation.year}</span> : null}
      </h4>
      <p className="mt-1 text-sm text-gold-400/90">
        Section {citation.section}
      </p>
      <p className="mt-3 line-clamp-5 text-sm leading-relaxed text-zinc-400">
        {citation.snippet}
      </p>
    </div>
  )
}
