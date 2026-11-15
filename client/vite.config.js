import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // Uvicorn's direct-development port. Docker-mapped or custom API ports can
  // be selected through VITE_API_PROXY_TARGET in the local .env file.
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: "127.0.0.1",
      proxy: {
        "/api": apiProxyTarget,
      },
    },
    build: {
      outDir: "dist",
      sourcemap: false,
    },
  };
});
