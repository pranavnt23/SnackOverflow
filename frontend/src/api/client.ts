/**
 * HTTP API client for Snack Overflow.
 * Wraps native fetch() to handle Bearer authentication, JSON serialisation,
 * standardized error unpacking, and session expiry redirects.
 */

import { ApiErrorEnvelope, ValidationErrorDetail } from './types';

export const TOKEN_STORAGE_KEY = 'snack_overflow_token';

/**
 * Custom error class representing API failures from the backend.
 * Unpacks the standardized envelope: {"error": {"code": "...", "message": "...", "details": [...]}}
 */
export class ApiError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly details?: ValidationErrorDetail[];

  constructor(status: number, code: string, message: string, details?: ValidationErrorDetail[]) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined | null>;
}

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

/**
 * Universal request wrapper for all HTTP operations against the FastAPI backend.
 */
export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers: customHeaders, ...fetchOptions } = options;

  // Build URL with query parameters
  const url = new URL(`${BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`);
  if (params) {
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        url.searchParams.append(key, String(val));
      }
    });
  }

  // Construct request headers
  const headers = new Headers(customHeaders);
  if (!headers.has('Content-Type') && !(fetchOptions.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  // Inject Bearer token from localStorage if available
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      ...fetchOptions,
      headers,
    });
  } catch (networkError) {
    // Network down or DNS failure
    throw new ApiError(
      0,
      'NETWORK_ERROR',
      'Unable to connect to the backend server. Please check your internet connection or server status.'
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  // Parse JSON response or handle empty response
  let data: any = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  }

  // Success handling (2xx)
  if (response.ok) {
    return data as T;
  }

  // 401 Unauthorized handling: Clear token and navigate to login
  if (response.status === 401) {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    // Only redirect if not already on the login page to avoid refresh loops
    if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
      window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
    }
  }

  // Extract structured error from backend envelope
  if (data && typeof data === 'object' && 'error' in data) {
    const errorPayload = (data as ApiErrorEnvelope).error;
    throw new ApiError(
      response.status,
      errorPayload.code || 'UNKNOWN_ERROR',
      errorPayload.message || 'An unexpected error occurred',
      errorPayload.details
    );
  }

  // Fallback for non-envelope errors (e.g. proxy gateways)
  throw new ApiError(
    response.status,
    'HTTP_ERROR',
    `Request failed with status ${response.status} (${response.statusText || 'Error'})`
  );
}

// Convenience REST helpers
export const apiClient = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: any, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),

  patch: <T>(endpoint: string, body?: any, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'DELETE' }),
};
