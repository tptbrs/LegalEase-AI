import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 120_000,
})

function unwrapError(err) {
  // Backend returned a response with our standard `detail` field.
  if (err.response?.data?.detail) return err.response.data.detail

  // Network-level failure (server not running, DNS, firewall, etc.).
  // Use a stable marker string that ErrorBlock can detect.
  const code = err.code || ''
  const msg = err.message || ''
  const isNetworkLevel =
    !err.response &&
    (code === 'ERR_NETWORK' ||
      code === 'ERR_CONNECTION_REFUSED' ||
      /network error/i.test(msg) ||
      /failed to fetch/i.test(msg))
  if (isNetworkLevel) return 'Backend unreachable'

  // Request was sent but the server took too long.
  if (code === 'ECONNABORTED') {
    return 'The request took too long. The backend may be busy or starting up — wait a few seconds and try again.'
  }

  return msg || 'Unknown error'
}

export async function postQA({
  query,
  language = 'en',
  history = [],
  documentContext = null,
}) {
  try {
    const { data } = await client.post('/qa', {
      query,
      language,
      history,
      document_context: documentContext,
    })
    return data
  } catch (err) {
    throw new Error(unwrapError(err))
  }
}

export async function postStrategy({ query, language = 'en', history = [] }) {
  try {
    const { data } = await client.post('/strategy', {
      query,
      language,
      history,
    })
    return data
  } catch (err) {
    throw new Error(unwrapError(err))
  }
}

export async function postFIR(payload) {
  try {
    const { data } = await client.post('/fir', payload)
    return data
  } catch (err) {
    throw new Error(unwrapError(err))
  }
}

export async function downloadFIRPdf(payload) {
  const response = await client.post('/fir/pdf', payload, { responseType: 'blob' })
  const url = window.URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  a.download = 'legalease_fir_draft.pdf'
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}

export async function postDocumentAnalysis({ file, concern = '', language = 'en' }) {
  const form = new FormData()
  form.append('file', file)
  form.append('concern', concern)
  form.append('language', language)
  try {
    const { data } = await client.post('/analyze-document', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  } catch (err) {
    throw new Error(unwrapError(err))
  }
}

