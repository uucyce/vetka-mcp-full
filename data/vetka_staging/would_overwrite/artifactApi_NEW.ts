import { Artifact } from '../types/artifact';

const API_BASE_URL = '/api';

interface ApiError {
  message: string;
  status?: number;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text();
    const error: ApiError = {
      message: errorText || `HTTP error! status: ${response.status}`,
      status: response.status
    };
    throw error;
  }
  
  try {
    return await response.json();
  } catch (error) {
    throw { message: 'Invalid JSON response' };
  }
}

/**
 * Fetch all artifacts from the backend
 * @returns Promise resolving to array of artifacts
 */
export async function fetchArtifacts(): Promise<Artifact[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/artifacts`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    return handleResponse<Artifact[]>(response);
  } catch (error) {
    console.error('Error fetching artifacts:', error);
    throw error;
  }
}

/**
 * Approve an artifact by ID
 * @param id - The ID of the artifact to approve
 * @returns Promise resolving to the updated artifact
 */
export async function approveArtifact(id: string): Promise<Artifact> {
  try {
    const response = await fetch(`${API_BASE_URL}/artifacts/${id}/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    return handleResponse<Artifact>(response);
  } catch (error) {
    console.error(`Error approving artifact ${id}:`, error);
    throw error;
  }
}

/**
 * Reject an artifact by ID
 * @param id - The ID of the artifact to reject
 * @returns Promise resolving to the updated artifact
 */
export async function rejectArtifact(id: string): Promise<Artifact> {
  try {
    const response = await fetch(`${API_BASE_URL}/artifacts/${id}/reject`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    return handleResponse<Artifact>(response);
  } catch (error) {
    console.error(`Error rejecting artifact ${id}:`, error);
    throw error;
  }
}