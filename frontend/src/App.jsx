import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Landing from './pages/Landing.jsx'
import Chat from './pages/Chat.jsx'
import FIRGenerator from './pages/FIRGenerator.jsx'
import DocumentUpload from './pages/DocumentUpload.jsx'
import Strategy from './pages/Strategy.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Landing />} />
        <Route path="chat" element={<Chat />} />
        <Route path="strategy" element={<Strategy />} />
        <Route path="fir" element={<FIRGenerator />} />
        <Route path="analyze" element={<DocumentUpload />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
