// file: client/src/store/useStore.ts

// MARKER_102.3_START
interface TreeState {
  // ... existing state properties ...

  // Artifact approval/rejection handlers
  approveArtifact: (id: string) => Promise<boolean>;
  rejectArtifact: (id: string) => Promise<boolean>;
  fetchArtifacts: () => Promise<void>;
}

export const useStore = create<TreeState>((set, get) => ({
  // ... existing store properties and methods ...

  approveArtifact: async (id: string) => {
    try {
      const response = await fetch(`/api/artifacts/${id}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        // Refetch artifacts on success
        await get().fetchArtifacts();
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error approving artifact:', error);
      return false;
    }
  },

  rejectArtifact: async (id: string) => {
    try {
      const response = await fetch(`/api/artifacts/${id}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        // Refetch artifacts on success
        await get().fetchArtifacts();
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error rejecting artifact:', error);
      return false;
    }
  },

  fetchArtifacts: async () => {
    try {
      const response = await fetch('/api/artifacts');
      if (response.ok) {
        const data = await response.json();
        // Update the nodes with the fetched artifacts
        if (data.artifacts) {
          const artifactNodes = data.artifacts.map((artifact: any) => ({
            id: artifact.id,
            path: `/artifacts/${artifact.id}`,
            name: artifact.id,
            type: 'artifact',
            backendType: 'leaf' as const,
            depth: 1,
            parentId: null,
            position: { x: 0, y: 0, z: 0 },
            color: '#4ade80',
            status: artifact.status,
          }));
          
          set({ 
            nodes: Object.fromEntries(artifactNodes.map((n: any) => [n.id, n]))
          });
        }
      }
    } catch (error) {
      console.error('Error fetching artifacts:', error);
    }
  },

  // ... rest of the store implementation ...
}));
// MARKER_102.3_END