/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        paper: {
          light: '#faf8f5',
          dark: '#1a1a1a',
          card: '#ffffff',
          border: '#e0e0e0',
        },
        cms: {
          sidebar: '#1e293b',
          background: '#f8fafc',
          card: '#ffffff',
        },
      },
      fontFamily: {
        serif: ['"Playfair Display"', '"Source Serif Pro"', 'Georgia', 'serif'],
        sans: ['"Inter"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
        body: ['"Lora"', '"Source Serif Pro"', 'serif'],
      },
    },
  },
  plugins: [],
}
