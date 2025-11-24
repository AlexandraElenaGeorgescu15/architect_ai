/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "#00437B", // Trimble Blue
          foreground: "#FFFFFF",
          dark: "#002D5B",
          mid: "#005F9E",
          light: "#009AD9",
        },
        secondary: {
          DEFAULT: "#363545", // Trimble Gray
          foreground: "#FFFFFF",
        },
        destructive: {
          DEFAULT: "#A51D25", // Trimble Red
          foreground: "#FFFFFF",
        },
        muted: {
          DEFAULT: "#F3F3F7", // Gray Light
          foreground: "#595868", // Gray 9
        },
        accent: {
          DEFAULT: "#FFBE00", // Trimble Yellow
          foreground: "#252A2E",
        },
        popover: {
          DEFAULT: "#FFFFFF",
          foreground: "#252A2E",
        },
        card: {
          DEFAULT: "#FFFFFF",
          foreground: "#252A2E",
        },
        trimble: {
          blue: {
            dark: "#002D5B",
            DEFAULT: "#00437B",
            mid: "#005F9E",
            light: "#009AD9",
            pale: "#BED6E7",
          },
          yellow: {
            DEFAULT: "#FFBE00",
            light: "#FFD200",
            dark: "#FFA500",
          },
          green: {
            DEFAULT: "#4D6F33",
            light: "#8DB938",
            dark: "#006638",
          },
          red: {
            DEFAULT: "#A51D25",
            light: "#EF7077",
            dark: "#890008",
          },
          gray: {
            DEFAULT: "#363545",
            light: "#F3F3F7",
            dark: "#262533",
          }
        }
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
}
