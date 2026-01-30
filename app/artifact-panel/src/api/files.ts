/**
 * Centralized API layer for file operations
 * Handles errors, retries, and timeouts
 */

interface FileContent {
  content: string;
  encoding: 'utf-8' | 'base64';
  mimeType: string;
  size?: number;
}

interface ApiError {
  code: string;
  message: string;
  status?: number;
}

const API_TIMEOUT = 300000; // 5 minutes for large artifacts
const RETRY_COUNT = 1;

/**
 * Wrap fetch with timeout
 */
async function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), API_TIMEOUT);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
}

/**
 * Normalize API errors
 */
function normalizeError(error: unknown): ApiError {
  if (error instanceof Error) {
    if (error.name === 'AbortError') {
      return {
        code: 'TIMEOUT',
        message: 'Request timeout (30s)',
      };
    }
    return {
      code: 'NETWORK_ERROR',
      message: error.message,
    };
  }
  return {
    code: 'UNKNOWN_ERROR',
    message: 'An unexpected error occurred',
  };
}

/**
 * Retry helper
 */
async function withRetry<T>(
  fn: () => Promise<T>,
  retries = RETRY_COUNT
): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    if (retries > 0) {
      console.warn(`[API] Retry attempt ${RETRY_COUNT - retries + 1}`);
      return withRetry(fn, retries - 1);
    }
    throw error;
  }
}

/**
 * Read file content
 */
export async function readFile(path: string): Promise<FileContent> {
  return withRetry(async () => {
    const response = await fetchWithTimeout('/api/files/read', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });

    if (!response.ok) {
      const error: ApiError = {
        code: `HTTP_${response.status}`,
        message: `Failed to read file: ${response.statusText}`,
        status: response.status,
      };
      throw error;
    }

    const data = await response.json();
    return data as FileContent;
  });
}

/**
 * Save file content
 */
export async function saveFile(path: string, content: string): Promise<void> {
  return withRetry(async () => {
    const response = await fetchWithTimeout('/api/files/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content }),
    });

    if (!response.ok) {
      const error: ApiError = {
        code: `HTTP_${response.status}`,
        message: `Failed to save file: ${response.statusText}`,
        status: response.status,
      };
      throw error;
    }
  });
}

/**
 * Get raw file URL (for media/images/PDF)
 */
export function getRawFileUrl(path: string): string {
  return `/api/files/raw?path=${encodeURIComponent(path)}`;
}

/**
 * Format error for display
 */
export function formatApiError(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return (error as { message: string }).message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An error occurred';
}

/**
 * Check if error is network-related
 */
export function isNetworkError(error: unknown): boolean {
  if (typeof error === 'object' && error !== null) {
    const err = error as { code?: string };
    return ['TIMEOUT', 'NETWORK_ERROR'].includes(err.code || '');
  }
  return false;
}
