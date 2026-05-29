import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 백엔드(FastAPI, 8000) 로 API 요청을 프록시하여 CORS 부담 없이 개발한다.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
