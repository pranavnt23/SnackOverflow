/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#fdf8f6',
          100: '#f2e8e5',
          200: '#eaddd7',
          500: '#ea580c', // Warm orange/cookie snack accent
          600: '#c2410c',
          700: '#9a3412',
        },
      },
    },
  },
  plugins: [],
}
