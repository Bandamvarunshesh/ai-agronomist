const defaultBaseUrl = import.meta.env.DEV ? "http://127.0.0.1:8000/api/v1" : "";
const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || defaultBaseUrl;

if (!configuredBaseUrl) {
  throw new Error("VITE_API_BASE_URL is required for this build");
}

export const API_BASE_URL = (
  configuredBaseUrl
).replace(/\/+$/, "");

const parsedRequestTimeoutMs = Number(
  import.meta.env.VITE_API_TIMEOUT_MS ||
    import.meta.env.VITE_API_REQUEST_TIMEOUT_MS ||
    20000,
);
const API_REQUEST_TIMEOUT_MS =
  Number.isFinite(parsedRequestTimeoutMs) && parsedRequestTimeoutMs > 0
    ? parsedRequestTimeoutMs
    : 20000;
const MAX_LOGGED_RESPONSE_BODY_CHARS = 20000;

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

export class ApiResponseParseError extends Error {
  status: number;
  rawBody: string;

  constructor(status: number, message: string, rawBody: string) {
    super(message);
    this.name = "ApiResponseParseError";
    this.status = status;
    this.rawBody = rawBody;
  }
}

export class ApiTimeoutError extends Error {
  constructor(message = "The API request timed out.") {
    super(message);
    this.name = "ApiTimeoutError";
  }
}

export class ApiNetworkError extends Error {
  constructor(message = "Unable to reach the API server.") {
    super(message);
    this.name = "ApiNetworkError";
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  authToken?: string | null;
  body?: BodyInit | JsonBody;
  logResponseBody?: boolean;
  timeoutMs?: number;
};

async function readResponseBody(
  response: Response,
  logResponseBody: boolean,
): Promise<string> {
  const text = await response.text();

  if (logResponseBody) {
    const body =
      text.length > MAX_LOGGED_RESPONSE_BODY_CHARS
        ? `${text.slice(0, MAX_LOGGED_RESPONSE_BODY_CHARS)}... [truncated]`
        : text;
    console.debug("API raw response body", {
      url: response.url,
      status: response.status,
      body,
    });
  }

  return text;
}

function parseJsonBody<T>(response: Response, rawBody: string): T {
  if (!rawBody.trim()) {
    throw new ApiResponseParseError(
      response.status,
      "API server returned an empty response.",
      rawBody,
    );
  }

  try {
    return JSON.parse(rawBody) as T;
  } catch (error) {
    throw new ApiResponseParseError(
      response.status,
      error instanceof Error
        ? `API server returned invalid JSON: ${error.message}`
        : "API server returned invalid JSON.",
      rawBody,
    );
  }
}

async function parseErrorBody(
  response: Response,
  logResponseBody: boolean,
): Promise<unknown> {
  const contentType = response.headers.get("content-type") || "";
  const text = await readResponseBody(response, logResponseBody);

  if (!text.trim()) {
    return null;
  }

  if (contentType.includes("application/json")) {
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }

  return text;
}

function stringifyUnknown(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) {
    return value;
  }

  if (value && typeof value === "object") {
    if ("msg" in value && typeof (value as { msg?: unknown }).msg === "string") {
      return (value as { msg: string }).msg;
    }
    if (
      "message" in value &&
      typeof (value as { message?: unknown }).message === "string"
    ) {
      return (value as { message: string }).message;
    }

    try {
      return JSON.stringify(value);
    } catch {
      return null;
    }
  }

  return null;
}

function getErrorDetail(data: unknown, response: Response): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => stringifyUnknown(item))
        .filter(Boolean);
      if (messages.length) {
        return messages.join("; ");
      }
    }

    const detailMessage = stringifyUnknown(detail);
    if (detailMessage) {
      return detailMessage;
    }
  }

  const directMessage = stringifyUnknown(data);
  if (directMessage) {
    return directMessage;
  }

  switch (response.status) {
    case 401:
      return "Please sign in again.";
    case 403:
      return "You do not have access to this resource.";
    case 404:
      return "The requested resource was not found.";
    case 422:
      return "Please check the submitted details and try again.";
    case 429:
      return "The service is receiving too many requests. Please wait a moment and try again.";
    case 500:
    case 502:
    case 503:
      return "The service is temporarily unavailable. Please try again shortly.";
    default:
      return `Request failed with status ${response.status}`;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    authToken,
    headers,
    body,
    logResponseBody = false,
    timeoutMs,
    ...rest
  } = options;
  const resolvedPath = path.startsWith("/") ? path : `/${path}`;
  const isFormData = body instanceof FormData;
  const requestHeaders = new Headers(headers);
  const requestTimeoutMs =
    timeoutMs !== undefined && Number.isFinite(timeoutMs) && timeoutMs > 0
      ? timeoutMs
      : API_REQUEST_TIMEOUT_MS;

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
    () => abortController.abort(),
    requestTimeoutMs,
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
    if (
      abortController.signal.aborted ||
      (error instanceof DOMException && error.name === "AbortError")
    ) {
      throw new ApiTimeoutError();
    }
    if (import.meta.env.DEV) {
      console.error("API network error", error);
    }
    throw new ApiNetworkError();
  }

  window.clearTimeout(timeoutHandle);

  if (!response.ok) {
    const errorData = await parseErrorBody(response, logResponseBody);
    throw new ApiError(
      response.status,
      getErrorDetail(errorData, response),
      errorData,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const rawBody = await readResponseBody(response, logResponseBody);
  return parseJsonBody<T>(response, rawBody);
}
