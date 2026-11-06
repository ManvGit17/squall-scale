import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base so the build works when served at any path — locally and,
// later, under a GitHub Pages project subpath — without a rebuild.
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { port: 8090 },
  preview: { port: 8090 },
});
