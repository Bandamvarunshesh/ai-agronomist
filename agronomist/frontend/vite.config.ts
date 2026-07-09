import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

function parsePort(value: string | undefined, fallback: number) {
  const port = Number(value);
  return !isNaN(port) && isFinite(port) && port > 0 ? port : fallback;
}

function validateProductionEnv(mode: string, env: Record<string, string>) {
  if (mode !== "production") {
    return;
  }

  const apiBaseUrl = env.VITE_API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new Error("VITE_API_BASE_URL is required for production builds");
  }

  try {
    new URL(apiBaseUrl);
  } catch {
    throw new Error("VITE_API_BASE_URL must be a valid absolute URL");
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  validateProductionEnv(mode, env);

  return {
    plugins: [react()],
    build: {
      target: "es2020",
      sourcemap: env.VITE_SOURCEMAP === "true",
    },
    server: {
      host: env.VITE_DEV_HOST || "127.0.0.1",
      port: parsePort(env.VITE_DEV_PORT, 5173),
    },
    preview: {
      host: env.VITE_PREVIEW_HOST || "127.0.0.1",
      port: parsePort(env.VITE_PREVIEW_PORT, 4173),
    },
  };
});
