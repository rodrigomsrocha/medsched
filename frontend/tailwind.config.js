/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#f1f5ff",
          100: "#e4ecff",
          500: "#2563eb",
          600: "#1d4ed8",
          700: "#1e3a8a",
        },
      },
      boxShadow: {
        brand: "0 10px 50px rgba(37,99,235,0.15)",
      },
    },
  },
  plugins: [],
};
