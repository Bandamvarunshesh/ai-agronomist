const defaultBaseUrl = import.meta.env.DEV ? "http://127.0.0.1:8000/api/v1" : "";
const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || defaultBaseUrl;

if (!configuredBaseUrl) {
  throw new Error("VITE_API_BASE_URL is required for this build");
}

export const API_BASE_URL = (
  configuredBaseUrl
).replace(/\/+$/, "");

const parsedRequestTimeoutMs = Number(import.meta.env.VITE_API_REQUEST_TIMEOUT_MS || 20000);
const API_REQUEST_TIMEOUT_MS =
  Number.isFinite(parsedRequestTimeoutMs) && parsedRequestTimeoutMs > 0
    ? parsedRequestTimeoutMs
    : 20000;

type JsonBody =
  | string
  | number
  | boolean
  | null
  | JsonBody[]
  | { [key: string]: JsonBody };

export class ApiError extends Error {
  status: number;
  detail: string;
  data: unknown;

  constructor(status: number, detail: string, data: unknown) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.data = data;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  authToken?: string | null;
  body?: BodyInit | JsonBody;
};

async function parseErrorBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return text || null;
}

function getErrorDetail(data: unknown, response: Response): string {
  if (typeof data === "string" && data.trim()) {
    return data;
  }

  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  return `Request failed with status ${response.status}`;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { authToken, headers, body, ...rest } = options;
  const resolvedPath = path.startsWith("/") ? path : `/${path}`;
  const isFormData = body instanceof FormData;
  const requestHeaders = new Headers(headers);

  requestHeaders.set("Accept", "application/json");

  if (authToken) {
    requestHeaders.set("Authorization", `Bearer ${authToken}`);
  }

  let requestBody: BodyInit | undefined;
  if (body !== undefined) {
    if (isFormData) {
      requestBody = body;
    } else if (
      typeof body === "string" ||
      body instanceof Blob ||
      body instanceof URLSearchParams
    ) {
      requestBody = body;
    } else {
      requestHeaders.set("Content-Type", "application/json");
      requestBody = JSON.stringify(body);
    }
  }

  const abortController = new AbortController();
  const timeoutHandle = window.setTimeout(
    () => abortController.abort("request_timeout"),
    API_REQUEST_TIMEOUT_MS,
  );

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${resolvedPath}`, {
      ...rest,
      headers: requestHeaders,
      body: requestBody,
      signal: abortController.signal,
    });
  } catch (error) {
    window.clearTimeout(timeoutHandle);
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("The API request timed out.");
    }
    throw new Error("Unable to reach the API server.");
  }

  window.clearTimeout(timeoutHandle);

  if (!response.ok) {
    const errorData = await parseErrorBody(response);
    throw new ApiError(
      response.status,
      getErrorDetail(errorData, response),
      errorData,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
