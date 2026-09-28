import type { Config } from "tailwindcss";
import tailwindAnimate from "tailwindcss-animate";

export default {
  darkMode: ["class"],
  content: ["./pages/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "1.25rem",
      screens: { "2xl": "1200px" },
    },
    extend: {
      colors: {
        "signal-blue": "var(--color-signal-blue)",
        "deep-dusk": "var(--color-deep-dusk)",
        "azure-crest": "var(--color-azure-crest)",
        "hover-glow": "var(--color-hover-glow)",
        "ink-black": "var(--color-ink-black)",
        carbon: "var(--color-carbon)",
        slate: "var(--color-slate)",
        steel: "var(--color-steel)",
        fog: "var(--color-fog)",
        mist: "var(--color-mist)",
        vapor: "var(--color-vapor)",
        frost: "var(--color-frost)",
        chalk: "var(--color-chalk)",
        bone: "var(--color-bone)",
        ash: "var(--color-ash)",
        neon: "var(--color-neon)",
        "cyan-veil": "var(--color-cyan-veil)",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))", foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))", "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))", "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))", ring: "hsl(var(--sidebar-ring))",
        },
      },
      fontFamily: {
        sans: ["var(--font-body)"],
        display: ["var(--font-heading)"],
        mono: ["var(--font-ui-monospace)"],
      },
      maxWidth: { page: "var(--page-max-width)" },
      borderRadius: {
        lg: "var(--radius-lg)", md: "var(--radius-md)", sm: "2px",
        card: "var(--radius-cards)", feature: "var(--radius-feature-cards)", mockup: "var(--radius-product-mockup)",
      },
      boxShadow: {
        subtle: "var(--shadow-subtle)", frame: "var(--shadow-subtle-2)", inset: "var(--shadow-lg)", highlight: "var(--shadow-lg-2)",
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [tailwindAnimate],
} satisfies Config;
