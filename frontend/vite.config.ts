import { defineConfig } from "vite";
import dyadComponentTagger from "@dyad-sh/react-vite-component-tagger";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig(() => ({
  server: {
    host: "::",
    port: 8080,
    // The frontend calls the API at the same origin (`/api/v1` in src/lib/api.ts),
    // so the dev server has to forward it or every workspace page renders its
    // empty state. Compose sets API_PROXY_TARGET; running `pnpm dev` directly
    // falls back to the backend's published port on the compose network.
    proxy: {
      "/api": {
        target: process.env.API_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  plugins: [dyadComponentTagger(), react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
