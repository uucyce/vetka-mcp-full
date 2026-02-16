import { useMutation, useQueryClient } from '@tanstack/react-query';
import { artifactApi } from '../services/artifactApi';
import { Artifact } from '../types/artifact';

interface UseArtifactMutationsProps {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export const useApproveArtifact = (props?: UseArtifactMutationsProps) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => artifactApi.approveArtifact(id),
    onMutate: async (id: string) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['artifacts'] });
      
      // Snapshot the previous value
      const previousArtifacts = queryClient.getQueryData<Artifact[]>(['artifacts']);
      
      // Optimistically update to the new value
      if (previousArtifacts) {
        queryClient.setQueryData<Artifact[]>(['artifacts'], 
          previousArtifacts.map(artifact => 
            artifact.id === id ? { ...artifact, status: 'approved' } : artifact
          )
        );
      }
      
      return { previousArtifacts };
    },
    onError: (err, variables, context) => {
      // Rollback to the previous value
      if (context?.previousArtifacts) {
        queryClient.setQueryData(['artifacts'], context.previousArtifacts);
      }
      props?.onError?.(err);
    },
    onSuccess: (data, variables, context) => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      props?.onSuccess?.();
    },
  });
};

export const useRejectArtifact = (props?: UseArtifactMutationsProps) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => artifactApi.rejectArtifact(id),
    onMutate: async (id: string) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['artifacts'] });
      
      // Snapshot the previous value
      const previousArtifacts = queryClient.getQueryData<Artifact[]>(['artifacts']);
      
      // Optimistically update to the new value
      if (previousArtifacts) {
        queryClient.setQueryData<Artifact[]>(['artifacts'], 
          previousArtifacts.map(artifact => 
            artifact.id === id ? { ...artifact, status: 'rejected' } : artifact
          )
        );
      }
      
      return { previousArtifacts };
    },
    onError: (err, variables, context) => {
      // Rollback to the previous value
      if (context?.previousArtifacts) {
        queryClient.setQueryData(['artifacts'], context.previousArtifacts);
      }
      props?.onError?.(err);
    },
    onSuccess: (data, variables, context) => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      props?.onSuccess?.();
    },
  });
};