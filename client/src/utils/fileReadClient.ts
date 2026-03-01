type FileReadEncoding = 'utf-8' | 'base64' | 'binary' | string;

export interface FileReadResponse {
  path: string;
  content: string;
  mimeType?: string;
  encoding?: FileReadEncoding;
  size?: number;
  createdAt?: number;
  modifiedAt?: number;
}

export class FileReadHttpError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'FileReadHttpError';
  }
}

interface CacheEntry {
  expiresAt: number;
  data?: FileReadResponse;
  errorStatus?: number;
}

interface ReadFileOptions {
  force?: boolean;
}

const SUCCESS_TTL_MS = 30_000;
const NOT_FOUND_TTL_MS = 15_000;
const CACHE_MAX = 800;
const MAX_CONCURRENT_REQUESTS = 6;
const MAX_PENDING_REQUESTS = 500;

const cache = new Map<string, CacheEntry>();
const inFlight = new Map<string, Promise<FileReadResponse>>();
const pendingQueue: Array<() => void> = [];
let activeRequests = 0;

function nowMs(): number {
  return Date.now();
}

function trimCacheIfNeeded(): void {
  if (cache.size < CACHE_MAX) {
    return;
  }
  const oldestKey = cache.keys().next().value;
  if (oldestKey) {
    cache.delete(oldestKey);
  }
}

function fromCache(path: string): CacheEntry | null {
  const entry = cache.get(path);
  if (!entry) {
    return null;
  }
  if (entry.expiresAt <= nowMs()) {
    cache.delete(path);
    return null;
  }
  return entry;
}

function cacheSuccess(path: string, data: FileReadResponse): void {
  trimCacheIfNeeded();
  cache.set(path, {
    expiresAt: nowMs() + SUCCESS_TTL_MS,
    data,
  });
}

function cacheNotFound(path: string): void {
  trimCacheIfNeeded();
  cache.set(path, {
    expiresAt: nowMs() + NOT_FOUND_TTL_MS,
    errorStatus: 404,
  });
}

function scheduleNext(): void {
  while (activeRequests < MAX_CONCURRENT_REQUESTS && pendingQueue.length > 0) {
    const job = pendingQueue.shift();
    if (!job) break;
    activeRequests += 1;
    job();
  }
}

async function enqueueNetworkRead<T>(work: () => Promise<T>): Promise<T> {
  return await new Promise<T>((resolve, reject) => {
    const run = () => {
      work()
        .then(resolve)
        .catch(reject)
        .finally(() => {
          activeRequests = Math.max(0, activeRequests - 1);
          scheduleNext();
        });
    };

    if (activeRequests < MAX_CONCURRENT_REQUESTS) {
      activeRequests += 1;
      run();
      return;
    }

    if (pendingQueue.length >= MAX_PENDING_REQUESTS) {
      reject(new FileReadHttpError(429, 'Too many pending file reads'));
      return;
    }

    pendingQueue.push(run);
  });
}

export async function readFileViaApi(path: string, options: ReadFileOptions = {}): Promise<FileReadResponse> {
  const normalizedPath = String(path || '').trim();
  if (!normalizedPath) {
    throw new FileReadHttpError(400, 'File path is empty');
  }

  if (!options.force) {
    const cached = fromCache(normalizedPath);
    if (cached?.data) {
      return cached.data;
    }
    if (cached?.errorStatus === 404) {
      throw new FileReadHttpError(404, `File not found: ${normalizedPath}`);
    }
    const pending = inFlight.get(normalizedPath);
    if (pending) {
      return pending;
    }
  }

  const request = enqueueNetworkRead(async () => {
    const response = await fetch('/api/files/read', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: normalizedPath }),
    });

    if (!response.ok) {
      if (response.status === 404) {
        cacheNotFound(normalizedPath);
      }
      throw new FileReadHttpError(response.status, `Failed to read file (${response.status})`);
    }

    const payload = await response.json() as FileReadResponse;
    cacheSuccess(normalizedPath, payload);
    return payload;
  });

  inFlight.set(normalizedPath, request);
  try {
    return await request;
  } finally {
    inFlight.delete(normalizedPath);
  }
}

export function clearFileReadCache(): void {
  cache.clear();
  inFlight.clear();
  pendingQueue.length = 0;
  activeRequests = 0;
}
