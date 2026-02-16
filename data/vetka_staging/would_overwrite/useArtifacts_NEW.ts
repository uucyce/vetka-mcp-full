import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { artifactApi } from '../services/artifactApi';
import { Artifact, ArtifactApiResponse } from '../types/artifact';

export const useArtifacts = () => {
  return useQuery<ArtifactApiResponse, Error>({
    queryKey: ['artifacts'],
    queryFn: artifactApi.getArtifacts,
  });
};

export const useApproveArtifact = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: artifactApi.approveArtifact,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
    },
  });
};

export const useRejectArtifact = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: artifactApi.rejectArtifact,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
    },
  });
};