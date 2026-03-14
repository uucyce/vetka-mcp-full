type LogLevel = "log" | "info" | "warn" | "error";

interface LogEntry {
  ts: string;
  level: LogLevel;
  text: string;
}

interface NetworkEntry {
  ts: string;
  method: string;
  url: string;
  status: number | null;
  ok: boolean | null;
  durationMs: number | null;
}

interface DebugBridgeAdapter {
  getSnapshot: () => unknown;
  getApis: () => Record<string, unknown>;
}

declare global {
  interface Window {
    debug?: {
      logs: (limit?: number) => LogEntry[];
      search: (query: string) => LogEntry[];
      errors: (limit?: number) => LogEntry[];
      warnings: (limit?: number) => LogEntry[];
      printLogs: () => LogEntry[];
      stats: () => Record<string, unknown>;
      inspect: (query: string) => string[];
      find: (query: string) => string[];
      functions: (query?: string) => string[];
      network: (query?: string, limit?: number) => NetworkEntry[];
      findRequest: (query: string) => NetworkEntry[];
      watch: (path: string, label?: string) => string;
    };
    __parallaxDebugBridgeInstalled__?: boolean;
    __parallaxDebugLogs__?: LogEntry[];
    __parallaxDebugNetwork__?: NetworkEntry[];
    __parallaxDebugWatchMap__?: Record<string, boolean>;
  }
}

function stringifyArgs(args: unknown[]) {
  return args
    .map((value) => {
      if (typeof value === "string") return value;
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    })
    .join(" ");
}

function collectPaths(value: unknown, prefix: string, depth: number, out: string[]) {
  if (depth < 0 || value === null || value === undefined) return;
  if (typeof value === "function") {
    out.push(prefix);
    return;
  }
  if (typeof value !== "object") {
    out.push(`${prefix}=${String(value)}`);
    return;
  }

  const entries = Array.isArray(value) ? value.entries() : Object.entries(value);
  for (const [key, child] of entries) {
    const path = Array.isArray(value) ? `${prefix}[${String(key)}]` : `${prefix}.${key}`;
    collectPaths(child, path, depth - 1, out);
  }
}

function getByPath(root: Record<string, unknown>, path: string): { holder: Record<string, unknown>; key: string; value: unknown } | null {
  const normalized = path.replace(/^window\./, "");
  const parts = normalized.split(".").filter(Boolean);
  if (!parts.length) return null;

  let current: unknown = root;
  for (let index = 0; index < parts.length - 1; index += 1) {
    if (!current || typeof current !== "object") return null;
    current = (current as Record<string, unknown>)[parts[index]];
  }

  if (!current || typeof current !== "object") return null;
  const holder = current as Record<string, unknown>;
  const key = parts[parts.length - 1];
  return { holder, key, value: holder[key] };
}

export function installDebugBridge(adapter: DebugBridgeAdapter) {
  if (!window.__parallaxDebugLogs__) window.__parallaxDebugLogs__ = [];
  if (!window.__parallaxDebugNetwork__) window.__parallaxDebugNetwork__ = [];
  if (!window.__parallaxDebugWatchMap__) window.__parallaxDebugWatchMap__ = {};

  if (!window.__parallaxDebugBridgeInstalled__) {
    const originalConsole = {
      log: console.log.bind(console),
      info: console.info.bind(console),
      warn: console.warn.bind(console),
      error: console.error.bind(console),
    };

    (["log", "info", "warn", "error"] as const).forEach((level) => {
      console[level] = (...args: unknown[]) => {
        window.__parallaxDebugLogs__!.push({
          ts: new Date().toISOString(),
          level,
          text: stringifyArgs(args),
        });
        if (window.__parallaxDebugLogs__!.length > 500) {
          window.__parallaxDebugLogs__ = window.__parallaxDebugLogs__!.slice(-500);
        }
        originalConsole[level](...args);
      };
    });

    const originalFetch = window.fetch.bind(window);
    window.fetch = async (...args: Parameters<typeof fetch>) => {
      const input = args[0];
      const method = (args[1]?.method || "GET").toUpperCase();
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const start = performance.now();
      try {
        const response = await originalFetch(...args);
        window.__parallaxDebugNetwork__!.push({
          ts: new Date().toISOString(),
          method,
          url,
          status: response.status,
          ok: response.ok,
          durationMs: Number((performance.now() - start).toFixed(2)),
        });
        return response;
      } catch (error) {
        window.__parallaxDebugNetwork__!.push({
          ts: new Date().toISOString(),
          method,
          url,
          status: null,
          ok: false,
          durationMs: Number((performance.now() - start).toFixed(2)),
        });
        throw error;
      }
    };

    window.__parallaxDebugBridgeInstalled__ = true;
  }

  window.debug = {
    logs(limit = 50) {
      return window.__parallaxDebugLogs__!.slice(-limit);
    },
    search(query: string) {
      const needle = query.toLowerCase();
      return window.__parallaxDebugLogs__!.filter((entry) => entry.text.toLowerCase().includes(needle));
    },
    errors(limit = 20) {
      return window.__parallaxDebugLogs__!.filter((entry) => entry.level === "error").slice(-limit);
    },
    warnings(limit = 20) {
      return window.__parallaxDebugLogs__!.filter((entry) => entry.level === "warn").slice(-limit);
    },
    printLogs() {
      const entries = window.__parallaxDebugLogs__!.slice(-50);
      entries.forEach((entry) => {
        console.info(`[debug:${entry.level}] ${entry.ts} ${entry.text}`);
      });
      return entries;
    },
    stats() {
      const snapshot = adapter.getSnapshot();
      return {
        logCount: window.__parallaxDebugLogs__!.length,
        networkCount: window.__parallaxDebugNetwork__!.length,
        watchedFunctions: Object.keys(window.__parallaxDebugWatchMap__!).length,
        snapshotKeys: snapshot && typeof snapshot === "object" ? Object.keys(snapshot as Record<string, unknown>) : [],
      };
    },
    inspect(query: string) {
      const roots = adapter.getApis();
      const haystack: string[] = [];
      Object.entries(roots).forEach(([key, value]) => collectPaths(value, key, 4, haystack));
      collectPaths(adapter.getSnapshot(), "snapshot", 4, haystack);
      const needle = query.toLowerCase();
      return haystack.filter((entry) => entry.toLowerCase().includes(needle)).slice(0, 100);
    },
    find(query: string) {
      return this.inspect(query);
    },
    functions(query = "") {
      const roots = adapter.getApis();
      const results: string[] = [];
      Object.entries(roots).forEach(([key, value]) => collectPaths(value, key, 4, results));
      const needle = query.toLowerCase();
      return results.filter((entry) => entry.includes(".") && entry.toLowerCase().includes(needle)).slice(0, 100);
    },
    network(query = "", limit = 20) {
      const needle = query.toLowerCase();
      const entries = needle
        ? window.__parallaxDebugNetwork__!.filter((entry) => entry.url.toLowerCase().includes(needle))
        : window.__parallaxDebugNetwork__!;
      return entries.slice(-limit);
    },
    findRequest(query: string) {
      return this.network(query, 50);
    },
    watch(path: string, label?: string) {
      const roots = { window, ...adapter.getApis() } as Record<string, unknown>;
      const direct = getByPath(roots, path) || getByPath(window as unknown as Record<string, unknown>, path);
      if (!direct) {
        throw new Error(`Unable to resolve watch path: ${path}`);
      }
      if (typeof direct.value !== "function") {
        throw new Error(`Target is not a function: ${path}`);
      }
      if (window.__parallaxDebugWatchMap__![path]) {
        return `already-watching:${path}`;
      }
      const original = direct.value as (...args: unknown[]) => unknown;
      direct.holder[direct.key] = (...args: unknown[]) => {
        console.info(`[watch:${label || path}]`, { args });
        return original(...args);
      };
      window.__parallaxDebugWatchMap__![path] = true;
      return `watching:${path}`;
    },
  };
}
