import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useI18n } from '../i18n/index.jsx'

const links = [
  { to: '/', key: 'home', end: true },
  { to: '/chat', key: 'chat' },
  { to: '/strategy', key: 'strategy' },
  { to: '/fir', key: 'fir' },
  { to: '/analyze', key: 'analyze' },
]

export default function Navbar() {
  const { t, lang, setLang } = useI18n()
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  // Close mobile menu whenever the route changes.
  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  // Lock body scroll while the mobile menu is open.
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [mobileOpen])

  return (
    <header className="sticky top-0 z-40 border-b border-white/5 bg-ink-900/85 backdrop-blur">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6">
        <NavLink to="/" className="flex items-center gap-2.5 text-lg shrink-0">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-gold-500/15 ring-1 ring-gold-500/40">
            <svg viewBox="0 0 24 24" className="h-4 w-4 text-gold-500" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <path d="M5 6h14M5 11h14M5 16h9" />
            </svg>
          </div>
          <span className="font-serif text-xl text-zinc-100">
            LegalEase <span className="text-gold-500">AI</span>
          </span>
        </NavLink>

        {/* Desktop links — visible at lg (1024px) and above */}
        <div className="hidden items-center gap-1 lg:flex">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `rounded-md px-3 py-1.5 text-sm transition-colors ${
                  isActive
                    ? 'bg-white/5 text-gold-400'
                    : 'text-zinc-400 hover:text-zinc-100'
                }`
              }
            >
              {t(`nav.${l.key}`)}
            </NavLink>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {/* Language toggle */}
          <div className="flex items-center gap-1 rounded-lg border border-white/10 bg-ink-800/60 p-0.5">
            <button
              onClick={() => setLang('en')}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                lang === 'en' ? 'bg-gold-500/15 text-gold-400' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              EN
            </button>
            <button
              onClick={() => setLang('hi')}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                lang === 'hi' ? 'bg-gold-500/15 text-gold-400' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              हिन्दी
            </button>
          </div>

          {/* Hamburger — visible below lg breakpoint (covers phones + tablets + small laptops) */}
          <button
            type="button"
            onClick={() => setMobileOpen((v) => !v)}
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileOpen}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-ink-800/60 text-zinc-200 transition-colors hover:border-gold-500/40 hover:text-gold-400 lg:hidden"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              {mobileOpen ? (
                <>
                  <path d="M6 6l12 12" />
                  <path d="M6 18L18 6" />
                </>
              ) : (
                <>
                  <path d="M4 7h16" />
                  <path d="M4 12h16" />
                  <path d="M4 17h16" />
                </>
              )}
            </svg>
          </button>
        </div>
      </nav>

      {/* Mobile / tablet drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            key="mobile-menu"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-white/5 bg-ink-900/95 backdrop-blur lg:hidden"
          >
            <div className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-3 sm:px-6">
              {links.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  end={l.end}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    `rounded-md px-3 py-2.5 text-base transition-colors ${
                      isActive
                        ? 'bg-gold-500/10 text-gold-400'
                        : 'text-zinc-300 hover:bg-white/5 hover:text-zinc-100'
                    }`
                  }
                >
                  {t(`nav.${l.key}`)}
                </NavLink>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
