// MARKER_102_1_START
export interface Artifact {
  id: string;
  content: string;
  type: string;
  status: string;
}

export interface ArtifactApiResponse {
  success: boolean;
  artifacts: Artifact[];
}

export interface SingleArtifactResponse {
  success: boolean;
  artifact: Artifact;
}

export interface ArtifactActionResponse {
  success: boolean;
  message: string;
}
// MARKER_102_1_END