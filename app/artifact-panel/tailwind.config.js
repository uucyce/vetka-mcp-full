/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        vetka: {
          bg: '#0a0a0a',
          surface: '#111111',
          border: '#222222',
          text: '#d4d4d4',
          muted: '#666666',
          accent: '#3b82f6',
        }
      }
    },
  },
  plugins: [],
}
