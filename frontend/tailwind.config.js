/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Primary accent — deep indigo/violet
        accent: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
        // Neutral surfaces
        surface: {
          900: '#0d0d0f',
          800: '#141417',
          700: '#1c1c21',
          600: '#25252c',
          500: '#2e2e38',
          400: '#3d3d4a',
          300: '#55555f',
        },
      },
      boxShadow: {
        card: '0 2px 8px rgba(0,0,0,0.35)',
        'card-hover': '0 6px 20px rgba(0,0,0,0.5)',
      },
    },
  },
  plugins: [],
}
