import { useState, useEffect } from 'react';
import { useArtifacts } from '../../hooks/useArtifacts';
import { ErrorBoundary } from '../../components/ErrorBoundary';
import styles from './ArtifactViewer.module.css';

interface ArtifactViewerProps {
  runId: string;
}

export function ArtifactViewer({ runId }: ArtifactViewerProps) {
  const { artifacts, isLoading, error, refetch } = useArtifacts(runId);
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null);

  useEffect(() => {
    if (artifacts && artifacts.length > 0 && !selectedArtifact) {
      setSelectedArtifact(artifacts[0].id);
    }
  }, [artifacts, selectedArtifact]);

  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading artifacts...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>
          <h3>Error loading artifacts</h3>
          <p>{error.message || 'Failed to load artifacts'}</p>
          <button onClick={() => refetch()} className={styles.retryButton}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!artifacts || artifacts.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.empty}>No artifacts found for this run</div>
      </div>
    );
  }

  const currentArtifact = artifacts.find(a => a.id === selectedArtifact) || artifacts[0];

  return (
    <ErrorBoundary name="ArtifactViewer">
      <div className={styles.container}>
        <div className={styles.header}>
          <h2>Artifacts</h2>
          <button onClick={() => refetch()} className={styles.refreshButton}>
            Refresh
          </button>
        </div>
        
        <div className={styles.content}>
          <div className={styles.sidebar}>
            <ul className={styles.artifactList}>
              {artifacts.map(artifact => (
                <li 
                  key={artifact.id} 
                  className={`${styles.artifactItem} ${artifact.id === selectedArtifact ? styles.selected : ''}`}
                  onClick={() => setSelectedArtifact(artifact.id)}
                >
                  {artifact.name}
                </li>
              ))}
            </ul>
          </div>
          
          <div className={styles.main}>
            {currentArtifact ? (
              <div className={styles.artifactContent}>
                <h3>{currentArtifact.name}</h3>
                <pre className={styles.artifactPreview}>
                  {JSON.stringify(currentArtifact.content, null, 2)}
                </pre>
              </div>
            ) : (
              <div className={styles.empty}>Select an artifact to view</div>
            )}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}