import { useState, useEffect } from 'react';
import { Artifact } from '../types/artifact';

interface UseArtifactsResult {
  artifacts: Artifact[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export const useArtifacts = (): UseArtifactsResult => {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState<number>(0);

  const refetch = () => {
    setRefresh(prev => prev + 1);
  };

  useEffect(() => {
    const fetchArtifacts = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const response = await fetch('/api/artifacts');
        
        if (!response.ok) {
          throw new Error(`Failed to fetch artifacts: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        setArtifacts(data.artifacts || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setIsLoading(false);
      }
    };

    fetchArtifacts();
  }, [refresh]);

  return {
    artifacts,
    isLoading,
    error,
    refetch
  };
};