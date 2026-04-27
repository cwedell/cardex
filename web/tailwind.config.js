/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        rarity: {
          common:    '#6b7280',
          uncommon:  '#22c55e',
          rare:      '#3b82f6',
          epic:      '#a855f7',
          legendary: '#f59e0b',
        },
        rally: {
          cream:  '#f2ece0',
          paper:  '#e8e0ce',
          paper2: '#dfd7c4',
          dark:   '#1a1108',
          red:    '#c0200f',
          gold:   '#b8873f',
          muted:  '#8a7a62',
          rule:   '#c8bfad',
        },
      },
      fontFamily: {
        display: ['"Arial Narrow"', 'Arial', 'sans-serif'],
        serif:   ['Georgia', '"Times New Roman"', 'serif'],
      },
      animation: {
        'slide-up':   'slideUp 0.35s ease-out',
        'fade-in':    'fadeIn 0.25s ease-out',
        'pulse-slow': 'pulse 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
