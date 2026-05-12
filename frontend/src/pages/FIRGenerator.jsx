import { useState } from 'react'
import { motion } from 'framer-motion'
import { useI18n } from '../i18n/index.jsx'
import { downloadFIRPdf, postFIR } from '../utils/api.js'
import LoadingDots from '../components/LoadingDots.jsx'
import ErrorBlock from '../components/ErrorBlock.jsx'
import PipelineTrace from '../components/PipelineTrace.jsx'

const EXAMPLE_INCIDENTS_EN = [
  {
    label: 'Phone snatched',
    description:
      "Someone snatched my mobile phone from my hand yesterday around 7 PM near the Sector 18 metro station. The person was on a motorcycle with a second rider, and they sped off into the crowd before I could react. I have the bills and IMEI number with me.",
  },
  {
    label: 'Threats from neighbour',
    description:
      "For the past two weeks my neighbour has been threatening me and my family. He has come to my door drunk on three occasions and shouted that he will harm us if we do not vacate. He banged on my door last night around 11 PM. Two other neighbours overheard.",
  },
  {
    label: 'Online harassment',
    description:
      "Someone is posting morphed photos of me on Instagram and Telegram, and is demanding ten thousand rupees to take them down. They have messaged me from an unknown number. I have screenshots of all the messages and the social-media URLs.",
  },
  {
    label: 'Theft from vehicle',
    description:
      "When I returned to my car at the mall parking lot around 9 PM, I found the rear window broken and my laptop bag missing along with my wallet. The CCTV camera in the parking area should have captured the incident.",
  },
]

const EXAMPLE_INCIDENTS_HI = [
  {
    label: 'फ़ोन छीना गया',
    description:
      "कल लगभग शाम 7 बजे सेक्टर 18 मेट्रो स्टेशन के पास किसी ने मेरे हाथ से मोबाइल फ़ोन छीन लिया। दो लोग मोटरसाइकिल पर थे और भीड़ में गायब हो गए। मेरे पास बिल और IMEI नंबर मौजूद है।",
  },
  {
    label: 'पड़ोसी की धमकी',
    description:
      "पिछले दो सप्ताह से मेरा पड़ोसी मुझे और मेरे परिवार को धमका रहा है। तीन बार वह नशे में मेरे दरवाज़े पर आकर कहा कि अगर हमने जगह नहीं छोड़ी तो वह नुकसान पहुँचाएगा। कल रात लगभग 11 बजे उसने दरवाज़ा ज़ोर से पीटा। दो और पड़ोसियों ने सुना।",
  },
  {
    label: 'ऑनलाइन उत्पीड़न',
    description:
      "कोई व्यक्ति मेरी मॉर्फ की हुई तस्वीरें Instagram और Telegram पर डाल रहा है और हटाने के बदले दस हज़ार रुपये मांग रहा है। उसने अज्ञात नंबर से संदेश भेजा है। मेरे पास सभी संदेशों और सोशल-मीडिया लिंक के स्क्रीनशॉट हैं।",
  },
  {
    label: 'गाड़ी से चोरी',
    description:
      "मॉल पार्किंग में लगभग रात 9 बजे लौटने पर मैंने देखा कि मेरी गाड़ी का पिछला शीशा टूटा हुआ था और मेरा लैपटॉप बैग व पर्स गायब थे। पार्किंग में लगा CCTV कैमरा घटना कैद कर सकता है।",
  },
]

export default function FIRGenerator() {
  const { t, lang } = useI18n()
  const [form, setForm] = useState({
    complainant_name: '',
    incident_location: '',
    incident_datetime: '',
    incident_description: '',
  })
  const [loading, setLoading] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [error, setError] = useState(null)
  const [response, setResponse] = useState(null)

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const fillExample = (description) => {
    setForm((prev) => ({ ...prev, incident_description: description }))
    // Bring the textarea into view (helpful on mobile).
    setTimeout(() => {
      const el = document.getElementById('incident-description')
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el?.focus()
    }, 0)
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!form.incident_description.trim() || loading) return
    setLoading(true)
    setError(null)
    setResponse(null)
    try {
      const data = await postFIR({ ...form, language: lang })
      setResponse(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const downloadPdf = async () => {
    setPdfLoading(true)
    try {
      await downloadFIRPdf({ ...form, language: lang })
    } catch (err) {
      setError(err.message)
    } finally {
      setPdfLoading(false)
    }
  }

  const examples = lang === 'hi' ? EXAMPLE_INCIDENTS_HI : EXAMPLE_INCIDENTS_EN
  const showExamples = !response && !loading && !form.incident_description.trim()

  return (
    <div>
      <header className="mb-8">
        <h1 className="heading-display text-4xl text-zinc-100">{t('fir.title')}</h1>
        <p className="mt-2 max-w-3xl text-zinc-400">{t('fir.subtitle')}</p>
      </header>

      {showExamples && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="card mb-5 p-5"
        >
          <p className="mb-3 text-xs uppercase tracking-wider text-zinc-500">
            {t('fir.examples_label')}
          </p>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {examples.map((ex, i) => (
              <button
                key={i}
                type="button"
                onClick={() => fillExample(ex.description)}
                className="rounded-lg border border-white/10 bg-ink-700/40 p-3 text-left transition-colors hover:border-gold-500/40 hover:bg-gold-500/5"
              >
                <p className="text-sm font-medium text-gold-400">{ex.label}</p>
                <p className="mt-1 line-clamp-2 text-xs text-zinc-400">
                  {ex.description}
                </p>
              </button>
            ))}
          </div>
        </motion.div>
      )}

      <form onSubmit={submit} className="card grid grid-cols-1 gap-4 p-5 md:grid-cols-2">
        <Field label={t('fir.complainant_name')}>
          <input
            className="input"
            value={form.complainant_name}
            onChange={update('complainant_name')}
          />
        </Field>
        <Field label={t('fir.incident_datetime')}>
          <input
            className="input"
            placeholder="e.g. 12 May 2026, 22:30"
            value={form.incident_datetime}
            onChange={update('incident_datetime')}
          />
        </Field>
        <Field label={t('fir.incident_location')} className="md:col-span-2">
          <input
            className="input"
            value={form.incident_location}
            onChange={update('incident_location')}
          />
        </Field>
        <Field label={t('fir.incident_description')} className="md:col-span-2">
          <textarea
            id="incident-description"
            className="input min-h-[160px] resize-y"
            placeholder={t('fir.incident_placeholder')}
            value={form.incident_description}
            onChange={update('incident_description')}
          />
        </Field>
        <div className="md:col-span-2 flex items-center justify-end">
          <button
            type="submit"
            disabled={loading || !form.incident_description.trim()}
            className="btn-primary"
          >
            {loading ? '…' : t('fir.generate')}
          </button>
        </div>
      </form>

      {loading && <LoadingDots label={t('common.loading')} />}

      <div className="mt-4">
        <ErrorBlock error={error} />
      </div>

      {response && (
        <motion.section
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-8 space-y-6"
        >
          <div className="card p-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="heading-display text-2xl text-zinc-100">
                {response.data?.fir_title || 'FIR Draft'}
              </h2>
              <button
                onClick={downloadPdf}
                disabled={pdfLoading}
                className="btn-outline-gold"
              >
                {pdfLoading ? '…' : t('fir.download_pdf')}
              </button>
            </div>

            {response.data?.complainant_summary && (
              <p className="text-sm leading-relaxed text-zinc-300">
                {response.data.complainant_summary}
              </p>
            )}

            {response.data?.incident_narrative && (
              <div className="mt-4 rounded-lg border border-white/5 bg-ink-700/40 p-4">
                <p className="whitespace-pre-line text-sm leading-relaxed text-zinc-200">
                  {response.data.incident_narrative}
                </p>
              </div>
            )}
          </div>

          {Array.isArray(response.data?.applicable_sections) &&
            response.data.applicable_sections.length > 0 && (
              <div className="card p-6">
                <h3 className="heading-display mb-4 text-xl text-zinc-100">
                  Applicable Sections
                </h3>
                <ul className="divide-y divide-white/5">
                  {response.data.applicable_sections.map((sec, i) => (
                    <li key={i} className="grid grid-cols-12 gap-3 py-3 text-sm">
                      <span className="col-span-5 text-zinc-300">{sec.act_name}</span>
                      <span className="col-span-2 font-mono text-gold-400">§ {sec.section}</span>
                      <span className="col-span-5 text-zinc-400">{sec.offence}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

          {response.data?.police_station_guidance && (
            <div className="card p-6">
              <h3 className="heading-display mb-2 text-xl text-zinc-100">
                Police Station Guidance
              </h3>
              <p className="text-sm leading-relaxed text-zinc-300">
                {response.data.police_station_guidance}
              </p>
            </div>
          )}

          {Array.isArray(response.data?.evidence_to_collect) &&
            response.data.evidence_to_collect.length > 0 && (
              <div className="card p-6">
                <h3 className="heading-display mb-3 text-xl text-zinc-100">
                  Evidence to Collect
                </h3>
                <ul className="space-y-1.5 text-sm text-zinc-300">
                  {response.data.evidence_to_collect.map((e, i) => (
                    <li key={i}>• {e}</li>
                  ))}
                </ul>
              </div>
            )}

          <PipelineTrace trace={response.pipeline_trace} />
        </motion.section>
      )}
    </div>
  )
}

function Field({ label, children, className = '' }) {
  return (
    <div className={className}>
      <label className="label">{label}</label>
      {children}
    </div>
  )
}
