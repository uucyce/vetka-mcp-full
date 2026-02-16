import { Artifact, ArtifactApiResponse, ArtifactActionResponse, SingleArtifactResponse } from '../types/artifact';

const API_BASE_URL = '/api';

export const artifactApi = {
  // GET /api/artifacts endpoint
  getArtifacts: async (): Promise<ArtifactApiResponse> => {
    const response = await fetch(`${API_BASE_URL}/artifacts`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch artifacts: ${response.statusText}`);
    }
    
    return response.json();
  },

  // GET /api/artifacts/{id} endpoint
  getArtifactById: async (id: string): Promise<SingleArtifactResponse> => {
    const response = await fetch(`${API_BASE_URL}/artifacts/${id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch artifact: ${response.statusText}`);
    }
    
    return response.json();
  },

  // POST /api/artifacts/{id}/approve endpoint
  approveArtifact: async (id: string): Promise<ArtifactActionResponse> => {
    const response = await fetch(`${API_BASE_URL}/artifacts/${id}/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status: 'approved' }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to approve artifact: ${response.statusText}`);
    }
    
    return response.json();
  },

  // POST /api/artifacts/{id}/reject endpoint
  rejectArtifact: async (id: string): Promise<ArtifactActionResponse> => {
    const response = await fetch(`${API_BASE_URL}/artifacts/${id}/reject`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status: 'rejected' }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to reject artifact: ${response.statusText}`);
    }
    
    return response.json();
  },
};