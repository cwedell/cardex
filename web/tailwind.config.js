/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Rarity tier palette
        rarity: {
          common:    '#6b7280',
          uncommon:  '#22c55e',
          rare:      '#3b82f6',
          epic:      '#a855f7',
          legendary: '#f59e0b',
        },
      },
      animation: {
        'slide-up': 'slideUp 0.35s ease-out',
        'fade-in':  'fadeIn 0.25s ease-out',
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
