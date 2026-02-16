import React, { useEffect, useMemo, useRef, useState } from 'react';
import vetkaIcon from './assets/vetka_gpt_1_UP1_PHalfa.png';
import { isTauri, openExternalWebWindow } from './config/tauri';

// MARKER_146.STEP2_NATIVE_BROWSER_SHELL_UI
// MARKER_146.STEP3_TWO_STEP_SAVE_UI_IMPL

type SaveFormat = 'md' | 'html';
type WebShellNavigatePayload = {
  url?: string;
  title?: string;
  save_path?: string | null;
  save_paths?: string[] | null;
};

type PageMode = 'preview' | 'live';

function parseInitialState() {
  const params = new URLSearchParams(window.location.search);
  const initialUrl = (params.get('url') || '').trim();
  const initialSavePath = (params.get('save_path') || '').trim();
  const rawSavePaths = (params.get('save_paths') || '').trim();
  let initialSavePaths: string[] = [];
  if (rawSavePaths) {
    try {
      const parsed = JSON.parse(rawSavePaths);
      if (Array.isArray(parsed)) {
        initialSavePaths = parsed
          .map((v) => String(v || '').trim())
          .filter(Boolean)
          .slice(0, 24);
      }
    } catch {
      initialSavePaths = [];
    }
  }
  return {
    initialUrl,
    initialSavePath,
    initialSavePaths,
  };
}

const DEFAULT_ADDRESS_SUGGESTIONS = [
  'https://google.com',
  'https://github.com',
  'https://x.com',
  'https://gmail.com',
  'https://youtube.com',
];

function normalizeAddressInput(raw: string): string {
  const value = (raw || '').trim();
  if (!value) return '';
  if (/^https?:\/\//i.test(value)) return value;
  if (/^localhost(:\d+)?(\/.*)?$/i.test(value)) return `http://${value}`;
  if (/^[\w.-]+\.[a-z]{2,}(\/.*)?$/i.test(value)) return `https://${value}`;
  return `https://duckduckgo.com/?q=${encodeURIComponent(value)}`;
}

const SearchIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="8" />
    <path d="m21 21-4.35-4.35" />
  </svg>
);

function fileNameFromUrl(url: string): string {
  try {
    const u = new URL(url);
    const host = u.hostname.replace(/^www\./, '');
    const slug = `${host}-${new Date().toISOString().slice(0, 10)}`
      .replace(/[^a-zA-Z0-9._-]+/g, '-')
      .replace(/-+/g, '-');
    return slug || 'web-page';
  } catch {
    return 'web-page';
  }
}

export default function WebShellStandalone() {
  const { initialUrl, initialSavePath, initialSavePaths } = useMemo(parseInitialState, []);
  const [currentUrl, setCurrentUrl] = useState(initialUrl);
  const [addressValue, setAddressValue] = useState(initialUrl);
  const [history, setHistory] = useState<string[]>(initialUrl ? [initialUrl] : []);
  const [historyIndex, setHistoryIndex] = useState(initialUrl ? 0 : -1);
  const [findValue, setFindValue] = useState('');
  const [status, setStatus] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [pageMode, setPageMode] = useState<PageMode>('preview');
  const [isSaving, setIsSaving] = useState(false);
  const [saveRing, setSaveRing] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveStep, setSaveStep] = useState<1 | 2>(1);
  const [saveName, setSaveName] = useState(fileNameFromUrl(initialUrl));
  const [saveFormat, setSaveFormat] = useState<SaveFormat>('md');
  const [savePath, setSavePath] = useState(initialSavePath);
  const [savePathSuggestions, setSavePathSuggestions] = useState<string[]>(() => {
    const merged = [initialSavePath, ...initialSavePaths].filter(Boolean);
    return Array.from(new Set(merged)).slice(0, 24);
  });
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const iframeCleanupRef = useRef<(() => void) | null>(null);
  const bootLoadedRef = useRef(false);
  const findRangesRef = useRef<Range[]>([]);
  const findIndexRef = useRef(-1);
  const findNeedRebuildRef = useRef(true);
  const findDebounceRef = useRef<number | null>(null);
  const loadRequestRef = useRef(0);
  const loadAbortRef = useRef<AbortController | null>(null);
  const historyIndexRef = useRef(initialUrl ? 0 : -1);
  const lastExternalOpenRef = useRef<string>('');

  const addressSuggestions = useMemo(() => {
    const merged = [...history.slice().reverse(), ...DEFAULT_ADDRESS_SUGGESTIONS];
    return Array.from(new Set(merged)).slice(0, 30);
  }, [history]);

  useEffect(() => {
    historyIndexRef.current = historyIndex;
  }, [historyIndex]);

  useEffect(() => {
    if (!initialUrl) return;
    if (bootLoadedRef.current) return;
    bootLoadedRef.current = true;
    void (async () => {
      await loadPreview(initialUrl);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialUrl]);

  useEffect(() => {
    if (!isTauri()) return;
    let unlisten: (() => void) | undefined;
    void (async () => {
      try {
        const { listen } = await import('@tauri-apps/api/event');
        unlisten = await listen<WebShellNavigatePayload>('vetka:web-shell:navigate', (event) => {
          const payload = event.payload || {};
          const nextUrl = String(payload.url || '').trim();
          const nextTitle = String(payload.title || '').trim();
          const incomingPath = String(payload.save_path || '').trim();
          const incomingPaths = Array.isArray(payload.save_paths)
            ? payload.save_paths.map((p) => String(p || '').trim()).filter(Boolean)
            : [];
          if (nextTitle) {
            document.title = nextTitle;
          }
          const merged = [incomingPath, ...incomingPaths].filter(Boolean);
          if (merged.length > 0) {
            setSavePathSuggestions((prev) => Array.from(new Set([...merged, ...prev])).slice(0, 24));
            // Always reset destination to nearest viewport path for each newly opened result.
            setSavePath(merged[0]);
          }
          if (!nextUrl) return;
          setAddressValue(nextUrl);
          pushHistory(nextUrl);
          void loadPreview(nextUrl);
        });
      } catch {
        // no-op
      }
    })();
    return () => {
      if (unlisten) unlisten();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    return () => {
      if (findDebounceRef.current !== null) {
        window.clearTimeout(findDebounceRef.current);
        findDebounceRef.current = null;
      }
      if (loadAbortRef.current) {
        loadAbortRef.current.abort();
        loadAbortRef.current = null;
      }
    };
  }, []);

  const pushHistory = (url: string) => {
    const clean = String(url || '').trim();
    if (!clean) return;
    setHistory((prev) => {
      const idx = historyIndexRef.current;
      const base = idx >= 0 ? prev.slice(0, idx + 1) : [];
      if (base[base.length - 1] === clean) return base;
      const next = [...base, clean];
      setHistoryIndex(next.length - 1);
      return next;
    });
  };

  const loadPreview = async (url: string) => {
    const reqId = ++loadRequestRef.current;
    if (loadAbortRef.current) {
      loadAbortRef.current.abort();
      loadAbortRef.current = null;
    }
    const controller = new AbortController();
    loadAbortRef.current = controller;
    setIsLoading(true);
    try {
      const resp = await fetch('/api/search/web-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, timeout_s: 14 }),
        signal: controller.signal,
      });
      const data = await resp.json();
      if (!resp.ok || !data?.success || !data?.html) {
        throw new Error(data?.error || `HTTP ${resp.status}`);
      }
      if (reqId !== loadRequestRef.current) return;

      const resolvedUrl = String(data.url || url);
      const frameBlocked = Boolean(data.frame_blocked);
      const autoLive = Boolean(data.is_probably_js_app) || frameBlocked;
      setPreviewHtml(String(data.html || ''));
      setCurrentUrl(resolvedUrl);
      setAddressValue(resolvedUrl);
      setPageMode(autoLive ? 'live' : 'preview');
      findRangesRef.current = [];
      findIndexRef.current = -1;
      findNeedRebuildRef.current = true;
      if (frameBlocked && isTauri() && lastExternalOpenRef.current !== resolvedUrl) {
        lastExternalOpenRef.current = resolvedUrl;
        void openExternalWebWindow(resolvedUrl, data.title || 'VETKA External Web');
        setStatus(`Frame-blocked site opened in external webview: ${data.title || resolvedUrl}`);
      } else {
        setStatus(autoLive ? `Loaded live mode: ${data.title || resolvedUrl}` : `Loaded: ${data.title || resolvedUrl}`);
      }
    } catch (e) {
      if ((e as Error)?.name === 'AbortError') return;
      if (reqId !== loadRequestRef.current) return;
      setPreviewHtml('');
      setStatus(`Load failed: ${(e as Error).message}`);
    } finally {
      if (reqId === loadRequestRef.current) {
        setIsLoading(false);
        loadAbortRef.current = null;
      }
    }
  };

  const navigate = async (target: string) => {
    const clean = normalizeAddressInput(target);
    if (!clean) {
      setStatus('Address is empty');
      return;
    }
    setStatus('');
    await loadPreview(clean);
    pushHistory(clean);
  };

  const goBack = async () => {
    if (historyIndex <= 0) return;
    const nextIdx = historyIndex - 1;
    const url = history[nextIdx];
    if (!url) return;
    setHistoryIndex(nextIdx);
    await loadPreview(url);
  };

  const goForward = async () => {
    if (historyIndex >= history.length - 1) return;
    const nextIdx = historyIndex + 1;
    const url = history[nextIdx];
    if (!url) return;
    setHistoryIndex(nextIdx);
    await loadPreview(url);
  };

  const rebuildFindRanges = () => {
    const q = findValue.trim().toLowerCase();
    findRangesRef.current = [];
    findIndexRef.current = -1;
    if (!q) return;
    try {
      const frameDoc = iframeRef.current?.contentDocument;
      if (!frameDoc?.body) return;
      const walker = frameDoc.createTreeWalker(frameDoc.body, NodeFilter.SHOW_TEXT);
      let node = walker.nextNode() as Text | null;
      while (node) {
        const text = node.nodeValue || '';
        const lower = text.toLowerCase();
        let from = 0;
        while (from < lower.length) {
          const idx = lower.indexOf(q, from);
          if (idx === -1) break;
          const range = frameDoc.createRange();
          range.setStart(node, idx);
          range.setEnd(node, idx + q.length);
          findRangesRef.current.push(range);
          from = idx + q.length;
        }
        node = walker.nextNode() as Text | null;
      }
    } catch {
      // no-op: blocked content
    }
  };

  const findInPage = (cycleNext: boolean = true) => {
    const q = findValue.trim();
    if (!q) {
      setStatus(currentUrl || 'Idle');
      return;
    }
    if (pageMode === 'live') {
      setStatus('Find unavailable in live mode for this site. Use preview mode.');
      return;
    }
    try {
      const quickFindWindow = iframeRef.current?.contentWindow as (Window & { find?: (...args: any[]) => boolean }) | null;
      if (cycleNext && quickFindWindow && typeof quickFindWindow.find === 'function') {
        const found = quickFindWindow.find(q, false, false, true, false, false, false);
        if (found) {
          setStatus(`Find: "${q}"`);
          return;
        }
      }

      if (findNeedRebuildRef.current) {
        rebuildFindRanges();
        findNeedRebuildRef.current = false;
      }
      const frameDoc = iframeRef.current?.contentDocument;
      const frameWin = iframeRef.current?.contentWindow;
      if (!frameDoc || !frameWin) return;
      const matches = findRangesRef.current;
      if (matches.length === 0) {
        setStatus('Find: no matches');
        return;
      }
      if (!cycleNext || findIndexRef.current < 0) {
        findIndexRef.current = 0;
      } else {
        findIndexRef.current = (findIndexRef.current + 1) % matches.length;
      }
      const active = matches[findIndexRef.current];
      const selection = frameWin.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(active);
      const parentEl = (active.startContainer as any)?.parentElement as HTMLElement | undefined;
      parentEl?.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
      setStatus(`Find: ${findIndexRef.current + 1}/${matches.length}`);
    } catch {
      setStatus('Find is unavailable for this site');
    }
  };

  const bindIframeNavigationBridge = () => {
    iframeCleanupRef.current?.();
    iframeCleanupRef.current = null;

    const frameDoc = iframeRef.current?.contentDocument;
    if (!frameDoc) return;

    const clickHandler = (ev: Event) => {
      const target = ev.target as HTMLElement | null;
      const anchor = target?.closest?.('a[href]') as HTMLAnchorElement | null;
      if (!anchor) return;
      const href = String(anchor.getAttribute('href') || '').trim();
      if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;

      try {
        const resolved = new URL(href, currentUrl || 'https://example.com').toString();
        if (!/^https?:\/\//i.test(resolved)) return;
        ev.preventDefault();
        ev.stopPropagation();
        void navigate(resolved);
      } catch {
        // ignore broken href
      }
    };

    const submitHandler = (ev: Event) => {
      const form = ev.target as HTMLFormElement | null;
      if (!form) return;
      const action = String(form.getAttribute('action') || '').trim();
      if (!action) return;
      try {
        const resolved = new URL(action, currentUrl || 'https://example.com').toString();
        if (!/^https?:\/\//i.test(resolved)) return;
        ev.preventDefault();
        ev.stopPropagation();
        void navigate(resolved);
      } catch {
        // ignore malformed action
      }
    };

    frameDoc.addEventListener('click', clickHandler, true);
    frameDoc.addEventListener('submit', submitHandler, true);

    iframeCleanupRef.current = () => {
      frameDoc.removeEventListener('click', clickHandler, true);
      frameDoc.removeEventListener('submit', submitHandler, true);
    };
  };

  useEffect(() => {
    return () => {
      iframeCleanupRef.current?.();
      iframeCleanupRef.current = null;
    };
  }, []);

  const openSaveFlow = () => {
    setSaveRing(true);
    setShowSaveModal(true);
    setSaveStep(1);
    if (!saveName.trim()) setSaveName(fileNameFromUrl(currentUrl));
    if (!savePath.trim() && savePathSuggestions.length > 0) {
      setSavePath(savePathSuggestions[0]);
    }
  };

  const saveToVetka = async () => {
    if (!currentUrl || isSaving) return;
    setIsSaving(true);
    setStatus('');
    try {
      const resp = await fetch('/api/artifacts/save-webpage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: currentUrl,
          title: saveName.trim() || fileNameFromUrl(currentUrl),
          snippet: '',
          output_format: saveFormat,
          file_name: saveName.trim() || fileNameFromUrl(currentUrl),
          target_node_path: savePath.trim(),
        }),
      });
      const data = await resp.json();
      if (!resp.ok || !data?.success) {
        throw new Error(data?.error || `HTTP ${resp.status}`);
      }
      setStatus(`Saved: ${data.filename}`);
      setShowSaveModal(false);
      setTimeout(() => setSaveRing(false), 1400);
    } catch (e) {
      setStatus(`Save failed: ${(e as Error).message}`);
      setSaveRing(false);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#0a0a0a', display: 'flex', flexDirection: 'column' }}>
      <div style={{
        height: 48,
        borderBottom: '1px solid #202020',
        background: '#080808',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '0 10px',
      }}>
        <button onClick={goBack} style={btnStyle} title="Back">{'<'}</button>
        <button onClick={goForward} style={btnStyle} title="Forward">{'>'}</button>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void navigate(addressValue);
          }}
          style={{ flex: 1, display: 'flex' }}
        >
          <input
            value={addressValue}
            onChange={(e) => setAddressValue(e.target.value)}
            list="vetka-address-suggestions"
            style={{
              width: '100%',
              height: 30,
              border: '1px solid #2d2d2d',
              background: '#111',
              color: '#ddd',
              borderRadius: 6,
              padding: '0 10px',
              fontSize: 12,
            }}
            placeholder="https://..."
          />
          <datalist id="vetka-address-suggestions">
            {addressSuggestions.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
        </form>
        <div style={{
          width: 170,
          height: 30,
          border: '1px solid #2d2d2d',
          background: '#111',
          borderRadius: 6,
          display: 'flex',
          alignItems: 'center',
          padding: '0 8px',
          gap: 6,
        }}>
          <span style={{ color: '#666', display: 'flex', alignItems: 'center' }}><SearchIcon /></span>
          <input
            value={findValue}
            onChange={(e) => {
              setFindValue(e.target.value);
              findNeedRebuildRef.current = true;
              if (findDebounceRef.current !== null) {
                window.clearTimeout(findDebounceRef.current);
              }
              findDebounceRef.current = window.setTimeout(() => findInPage(false), 180);
            }}
            onKeyDown={(e) => { if (e.key === 'Enter') findInPage(true); }}
            style={{
              width: '100%',
              height: 24,
              border: 'none',
              outline: 'none',
              background: 'transparent',
              color: '#ccc',
              fontSize: 12,
            }}
            placeholder="find in page"
            title="Type to search on page. Enter for next match."
          />
        </div>
        <button
          onClick={() => setPageMode((m) => (m === 'live' ? 'preview' : 'live'))}
          style={{ ...btnStyle, width: 34 }}
          title={pageMode === 'live' ? 'Switch to preview mode (find works here)' : 'Switch to live mode'}
        >
          {pageMode === 'live' ? 'L' : 'P'}
        </button>
        <button
          onClick={openSaveFlow}
          title="save to vetka"
          style={{
            ...btnStyle,
            width: 34,
            height: 34,
            padding: 2,
            borderRadius: '50%',
            border: saveRing ? '1px solid #fff' : '1px solid #2d2d2d',
          }}
        >
          <img src={vetkaIcon} alt="save to vetka" style={{ width: 24, height: 24, objectFit: 'contain' }} />
        </button>
      </div>

      <div style={{ flex: 1, background: '#fff' }}>
        {isLoading ? (
          <div style={{ color: '#666', padding: 18, fontSize: 13 }}>Loading page preview...</div>
        ) : currentUrl ? (
          pageMode === 'live' ? (
            <iframe
              ref={iframeRef}
              title="VETKA Web Shell Live"
              src={currentUrl}
              style={{ width: '100%', height: '100%', border: 'none' }}
              sandbox="allow-same-origin allow-scripts allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation allow-downloads"
            />
          ) : (
            <iframe
              ref={iframeRef}
              title="VETKA Web Shell"
              srcDoc={previewHtml}
              onLoad={bindIframeNavigationBridge}
              style={{ width: '100%', height: '100%', border: 'none' }}
              sandbox="allow-same-origin allow-scripts allow-forms allow-modals allow-popups allow-downloads"
            />
          )
        ) : (
          <div style={{ color: '#888', padding: 18, fontSize: 13 }}>
            Open any web result from VETKA search to start browsing.
          </div>
        )}
      </div>

      <div style={{ height: 26, borderTop: '1px solid #202020', color: '#8a8a8a', background: '#0b0b0b', fontSize: 11, padding: '5px 10px' }}>
        {status || currentUrl || 'Idle'}
      </div>

      {showSaveModal && (
        <div style={overlayStyle}>
          <div style={modalStyle}>
            {saveStep === 1 ? (
              <>
                <div style={titleStyle}>Save to VETKA — Step 1/2</div>
                <input
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  style={inputStyle}
                  placeholder="File name"
                />
                <div style={{ display: 'flex', gap: 8 }}>
                  <button onClick={() => setSaveFormat('md')} style={{ ...modeBtn, ...(saveFormat === 'md' ? modeBtnOn : {}) }}>MD</button>
                  <button onClick={() => setSaveFormat('html')} style={{ ...modeBtn, ...(saveFormat === 'html' ? modeBtnOn : {}) }}>HTML</button>
                </div>
                <div style={rowStyle}>
                  <button onClick={() => { setShowSaveModal(false); setSaveRing(false); }} style={ghostBtn}>Cancel</button>
                  <button onClick={() => setSaveStep(2)} style={solidBtn}>Next</button>
                </div>
              </>
            ) : (
              <>
                <div style={titleStyle}>Save to VETKA — Step 2/2</div>
                <input
                  value={savePath}
                  onChange={(e) => setSavePath(e.target.value)}
                  list="vetka-save-paths"
                  style={inputStyle}
                  placeholder="Destination path (nearest viewport path by default)"
                />
                <datalist id="vetka-save-paths">
                  {savePathSuggestions.map((p) => (
                    <option key={p} value={p} />
                  ))}
                </datalist>
                {savePathSuggestions.length > 0 && (
                  <div style={{
                    maxHeight: 94,
                    overflowY: 'auto',
                    border: '1px solid #242424',
                    borderRadius: 6,
                    padding: 6,
                    background: '#101010',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                  }}>
                    {savePathSuggestions.slice(0, 8).map((p) => (
                      <button
                        key={p}
                        onClick={() => setSavePath(p)}
                        style={{
                          textAlign: 'left',
                          background: savePath === p ? '#202020' : 'transparent',
                          color: '#bcbcbc',
                          border: '1px solid #2a2a2a',
                          borderRadius: 5,
                          padding: '4px 6px',
                          cursor: 'pointer',
                          fontSize: 11,
                          fontFamily: 'monospace',
                        }}
                        title={p}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                )}
                <div style={{ color: '#8e8e8e', fontSize: 11 }}>
                  Current URL: {currentUrl}
                </div>
                <div style={rowStyle}>
                  <button onClick={() => setSaveStep(1)} style={ghostBtn}>Back</button>
                  <button onClick={saveToVetka} style={solidBtn} disabled={isSaving}>{isSaving ? 'Saving...' : 'Save'}</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  width: 30,
  height: 30,
  border: '1px solid #2d2d2d',
  background: '#111',
  color: '#e8e8e8',
  borderRadius: 6,
  cursor: 'pointer',
  fontSize: 12,
};

const overlayStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.65)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 9999,
};

const modalStyle: React.CSSProperties = {
  width: 520,
  background: '#0f0f0f',
  border: '1px solid #2c2c2c',
  borderRadius: 10,
  padding: 14,
  color: '#ddd',
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
};

const titleStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: '#f0f0f0',
};

const inputStyle: React.CSSProperties = {
  height: 34,
  border: '1px solid #2d2d2d',
  background: '#111',
  color: '#ddd',
  borderRadius: 6,
  padding: '0 10px',
  fontSize: 12,
};

const rowStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 8,
};

const modeBtn: React.CSSProperties = {
  height: 30,
  padding: '0 12px',
  border: '1px solid #2f2f2f',
  background: '#111',
  color: '#bbb',
  borderRadius: 6,
  cursor: 'pointer',
};

const modeBtnOn: React.CSSProperties = {
  border: '1px solid #626262',
  color: '#fff',
};

const ghostBtn: React.CSSProperties = {
  height: 32,
  padding: '0 12px',
  border: '1px solid #2f2f2f',
  background: '#111',
  color: '#ccc',
  borderRadius: 6,
  cursor: 'pointer',
};

const solidBtn: React.CSSProperties = {
  height: 32,
  padding: '0 12px',
  border: '1px solid #3f3f3f',
  background: '#1d1d1d',
  color: '#fff',
  borderRadius: 6,
  cursor: 'pointer',
};
