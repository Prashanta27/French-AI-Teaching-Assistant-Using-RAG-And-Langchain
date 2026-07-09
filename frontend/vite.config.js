import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server on 5173 (Vite default). FastAPI runs on 8000 -- see README
// for the CORS snippet you need to add to your FastAPI app so the
// browser is allowed to call it from a different port/origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
