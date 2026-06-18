/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        app: "#06111f",
        sidebar: "#071626",
        panel: "#0b1b2d",
        panelSoft: "#0e2238",
        line: "#14304a",
        muted: "#7fa2c4",
        cyan: "#22d3ee",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(34, 211, 238, 0.14), 0 18px 50px rgba(0, 0, 0, 0.24)",
      },
    },
  },
  plugins: [],
};
