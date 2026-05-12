import { useState } from 'react'
import { useI18n } from '../i18n/index.jsx'
import { postQA } from '../utils/api.js'
import ChatThread from '../components/ChatThread.jsx'

const SUGGESTIONS_EN = [
  "Can the police arrest me without a warrant?",
  "What are my rights if my employer doesn't pay overtime?",
  "How do I file a consumer complaint against an e-commerce seller?",
  "What is anticipatory bail and when can I apply for it?",
]

const SUGGESTIONS_HI = [
  "क्या पुलिस बिना वारंट के मुझे गिरफ्तार कर सकती है?",
  "यदि नियोक्ता ओवरटाइम का भुगतान नहीं करता तो मेरे क्या अधिकार हैं?",
  "ई-कॉमर्स विक्रेता के खिलाफ उपभोक्ता शिकायत कैसे दर्ज करें?",
  "अग्रिम जमानत क्या है और कब आवेदन कर सकते हैं?",
]

export default function Chat() {
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
      const data = await postQA({ query: text, language: lang, history })
      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.data?.answer || '(no answer)',
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
          <h1 className="heading-display text-4xl text-zinc-100">{t('chat.title')}</h1>
          <p className="mt-2 max-w-3xl text-zinc-400">{t('chat.subtitle')}</p>
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
        placeholder={t('chat.placeholder')}
        suggestions={lang === 'hi' ? SUGGESTIONS_HI : SUGGESTIONS_EN}
      />
    </div>
  )
}
