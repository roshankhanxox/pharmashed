import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // Dev: proxy /api/* to FastAPI (running on 8000)
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
