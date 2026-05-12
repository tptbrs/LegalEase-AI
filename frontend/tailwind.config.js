/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          900: '#0a0a0b',
          800: '#111114',
          700: '#17171c',
          600: '#1f1f26',
          500: '#2a2a33',
        },
        gold: {
          400: '#e9c876',
          500: '#d4af37',
          600: '#b8932a',
        },
        accent: {
          danger: '#e0625e',
          warning: '#e7b75f',
          success: '#7fc28a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['"Cormorant Garamond"', 'Georgia', 'serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        gold: '0 0 0 1px rgba(212, 175, 55, 0.25), 0 8px 32px -8px rgba(212, 175, 55, 0.18)',
        card: '0 1px 0 0 rgba(255,255,255,0.04) inset, 0 8px 32px -16px rgba(0,0,0,0.6)',
      },
      animation: {
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        shimmer: 'shimmer 2s linear infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
      },
    },
  },
  plugins: [],
}
