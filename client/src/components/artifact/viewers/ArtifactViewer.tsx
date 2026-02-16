import React, { useState, useEffect } from 'react';

interface Artifact {
  id: string;
  name: string;
  type: string;
  data: any;
}

const ArtifactViewer: React.FC = () => {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // MARKER_102_1_START
  useEffect(() => {
    const fetchArtifacts = async () => {
      try {
        const response = await fetch('/api/artifacts');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setArtifacts(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchArtifacts();
  }, []);
  // MARKER_102_1_END

  if (loading) {
    return <div className="artifact-viewer">Loading artifacts...</div>;
  }

  if (error) {
    return <div className="artifact-viewer error">Error: {error}</div>;
  }

  return (
    <div className="artifact-viewer">
      <h2>Artifacts</h2>
      {artifacts.length === 0 ? (
        <p>No artifacts found</p>
      ) : (
        <ul>
          {artifacts.map((artifact) => (
            <li key={artifact.id}>
              <strong>{artifact.name}</strong> ({artifact.type})
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default ArtifactViewer;