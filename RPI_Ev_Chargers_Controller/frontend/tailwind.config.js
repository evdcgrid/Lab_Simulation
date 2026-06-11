/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "Consolas", "monospace"]
      },
      colors: {
        graphite: {
          950: "#080a0d",
          900: "#0d1014",
          850: "#12161b",
          800: "#171c22",
          700: "#262d35"
        },
        signal: {
          green: "#36d399",
          cyan: "#22d3ee",
          amber: "#fbbf24",
          red: "#fb7185",
          steel: "#a7b0bc"
        }
      },
      boxShadow: {
        panel: "0 18px 45px rgba(0, 0, 0, 0.28)"
      }
    }
  },
  plugins: []
};

