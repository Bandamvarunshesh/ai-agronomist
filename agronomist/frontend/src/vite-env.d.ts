/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_REQUEST_TIMEOUT_MS?: string;
  readonly VITE_DEV_HOST?: string;
  readonly VITE_DEV_PORT?: string;
  readonly VITE_PREVIEW_HOST?: string;
  readonly VITE_PREVIEW_PORT?: string;
  readonly VITE_SOURCEMAP?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
