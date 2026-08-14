/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx}",
    "./components/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0C0F14",
        panel: "#151A24",
        raised: "#1C2230",
        line: "#282F40",
        brass: {
          DEFAULT: "#C99A44",
          dim: "#8A6C33",
          bright: "#E3B564",
        },
        teal: {
          DEFAULT: "#48C9B0",
          dim: "#2F8A78",
        },
        coral: "#E2574C",
        amber: "#E0A63E",
        ink2: "#E7E3DA",
        muted: "#8B92A3",
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        body: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      backgroundImage: {
        "dial-radial": "radial-gradient(circle at 50% 35%, rgba(201,154,68,0.14), transparent 60%)",
        "grain": "url('/grain.svg')",
      },
      boxShadow: {
        vault: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 20px 60px -20px rgba(0,0,0,0.6)",
      },
    },
  },
  plugins: [],
};
