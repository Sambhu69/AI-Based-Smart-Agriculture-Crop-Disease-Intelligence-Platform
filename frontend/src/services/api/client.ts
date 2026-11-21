/**
 * Centralized API Client for Smart Agriculture FastAPI Backend (/api/v1)
 */

const STORAGE_KEY_API_URL = 'agri_api_base_url';

export function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const stored = window.localStorage.getItem(STORAGE_KEY_API_URL);
    if (stored && stored.trim()) {
      return stored.trim().replace(/\/+$/, '');
    }
  }
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  return (envUrl || 'http://127.0.0.1:8000').replace(/\/+$/, '');
}

export function setApiBaseUrl(url: string): void {
  if (typeof window !== 'undefined') {
    const cleaned = url.trim().replace(/\/+$/, '');
    if (cleaned) {
      window.localStorage.setItem(STORAGE_KEY_API_URL, cleaned);
    } else {
      window.localStorage.removeItem(STORAGE_KEY_API_URL);
    }
  }
}

export class ApiClientError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiClientError';
    this.status = status;
    this.detail = detail;
  }
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') {
      return body.detail;
    }
    if (Array.isArray(body?.detail)) {
      return body.detail
        .map((e: { loc?: (string | number)[]; msg?: string }) =>
          `${(e.loc || []).slice(1).join('.')}: ${e.msg || 'Invalid value'}`
        )
        .join('; ');
    }
    if (typeof body?.error === 'string') {
      return `${body.error}: ${body.detail || response.statusText}`;
    }
  } catch {
    // Fallback to status text
  }
  return `HTTP ${response.status}: ${response.statusText || 'Request failed'}`;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = 15000
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${baseUrl}${normalizedPath}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    if (!response.ok) {
      const detail = await parseErrorDetail(response);
      throw new ApiClientError(response.status, detail);
    }

    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof ApiClientError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiClientError(408, `Request timed out after ${timeoutMs / 1000}s`);
    }
    throw new ApiClientError(
      0,
      `Unable to reach FastAPI server at ${baseUrl}. Ensure 'uvicorn app.main:app --port 8000' is running.`
    );
  } finally {
    clearTimeout(timer);
  }
}
