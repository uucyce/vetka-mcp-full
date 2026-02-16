// MARKER_102_1_START
export interface Artifact {
  id: string;
  content: string;
  type: 'code' | 'markdown' | 'image' | 'text' | string;
  status: 'pending' | 'approved' | 'rejected' | 'error' | string;
  createdAt?: string;
  updatedAt?: string;
  metadata?: Record<string, any>;
  version?: number;
}

export interface ArtifactApiResponse {
  success: boolean;
  artifacts: Artifact[];
  totalCount?: number;
  page?: number;
  pageSize?: number;
}

export interface SingleArtifactResponse {
  success: boolean;
  artifact: Artifact;
}

export interface ArtifactActionResponse {
  success: boolean;
  message: string;
  artifact?: Artifact;
}

export interface ArtifactListParams {
  page?: number;
  pageSize?: number;
  status?: string;
  type?: string;
}

export interface ArtifactUpdatePayload {
  status?: 'approved' | 'rejected';
  content?: string;
  metadata?: Record<string, any>;
}
// MARKER_102_1_END