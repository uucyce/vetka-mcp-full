import { useEffect, useMemo } from 'react';
import { ArtifactPanel } from './components/artifact/ArtifactPanel';
import { closeArtifactMediaWindow, isTauri } from './config/tauri';
import { installDetachedMediaDebug } from './utils/detachedMediaDebug';

function decodeParam(value: string | null): string {
  const raw = String(value || '').trim();
  if (!raw) return '';
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

function parseQuery() {
  const params = new URLSearchParams(window.location.search);
  const path = decodeParam(params.get('path'));
  const name = decodeParam(params.get('name'));
  const extension = decodeParam(params.get('extension')).replace(/^\./, '');
  const artifactId = decodeParam(params.get('artifact_id'));
  const inVetkaRaw = decodeParam(params.get('in_vetka'));
  const inVetka = inVetkaRaw === '1' ? true : (inVetkaRaw === '0' ? false : undefined);
  const seekRaw = decodeParam(params.get('seek'));
  const hasSeek = seekRaw !== '';
  const seekNum = hasSeek ? Number(seekRaw) : NaN;
  const initialSeekSec = hasSeek && Number.isFinite(seekNum) && seekNum >= 0 ? seekNum : undefined;

  const fallbackName = path.replace(/\\/g, '/').split('/').pop() || 'media';
  return {
    path,
    name: name || fallbackName,
    extension: extension || undefined,
    artifactId: artifactId || undefined,
    inVetka,
    initialSeekSec,
  };
}

export default function ArtifactMediaStandalone() {
  const query = useMemo(parseQuery, []);

  useEffect(() => {
    if (!query.path) return undefined;
    return installDetachedMediaDebug({
      path: query.path,
      name: query.name,
    });
  }, [query.name, query.path]);

  const handleClose = async () => {
    if (!isTauri()) {
      window.close();
      return;
    }
    const closed = await closeArtifactMediaWindow('artifact-media');
    if (!closed) window.close();
  };

  if (!query.path) {
    return (
      <div
        style={{
          width: '100vw',
          height: '100vh',
          display: 'grid',
          placeItems: 'center',
          background: '#0a0a0a',
          color: '#bcbcbc',
          fontSize: 14,
        }}
      >
        Missing media path
      </div>
    );
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: '#0a0a0a', overflow: 'hidden' }}>
      <ArtifactPanel
        file={{ path: query.path, name: query.name, extension: query.extension }}
        onClose={() => { void handleClose(); }}
        isChatOpen={false}
        artifactId={query.artifactId}
        detachedInitialInVetka={query.inVetka}
        initialSeekSec={query.initialSeekSec}
        windowMode="detached"
        detachedWindowLabel="artifact-media"
      />
    </div>
  );
}
