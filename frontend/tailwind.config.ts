import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          50:  "#e6f4ec",
          100: "#c2e0ce",
          200: "#8fc6a8",
          300: "#5aab81",
          400: "#2e9460",
          500: "#00713A",
          600: "#006633",
          700: "#005229",
          800: "#003d1e",
        },
      },
      keyframes: {
        "fade-up": {
          "0%":   { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "dot-bounce": {
          "0%, 80%, 100%": { transform: "scale(0.55)", opacity: "0.35" },
          "40%":           { transform: "scale(1)",    opacity: "1" },
        },
      },
      animation: {
        "fade-up":    "fade-up 0.18s ease-out",
        "dot-bounce": "dot-bounce 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
