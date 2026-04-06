import { useState, useEffect } from 'react';
import { Loader2, Check, X, AlertCircle } from 'lucide-react';
import { CodeViewer } from '../artifact/viewers/CodeViewer';
import { MarkdownViewer } from '../artifact/viewers/MarkdownViewer';
import { ImageViewer } from '../artifact/viewers/ImageViewer';
import { apiService } from '../../services/api';
import { Artifact } from '../../types/artifact';

interface ArtifactViewerProps {
  artifactId: string;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
}

export function ArtifactViewer({ artifactId, onApprove, onReject }: ArtifactViewerProps) {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch artifact data from API
  useEffect(() => {
    const fetchArtifact = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiService.getArtifact(artifactId);
        if (response.success) {
          setArtifact(response.artifact);
        } else {
          setError('Failed to load artifact');
        }
      } catch (err) {
        setError('Error fetching artifact');
        console.error('Artifact fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    if (artifactId) {
      fetchArtifact();
    }
  }, [artifactId]);

  const handleApprove = async () => {
    if (!artifact) return;
    
    try {
      setLoading(true);
      const response = await apiService.approveArtifact(artifact.id);
      if (response.success && onApprove) {
        onApprove(artifact.id);
        // Update local state to reflect approval
        setArtifact(prev => prev ? {...prev, status: 'approved'} : null);
      }
    } catch (err) {
      setError('Failed to approve artifact');
      console.error('Approval error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!artifact) return;
    
    try {
      setLoading(true);
      const response = await apiService.rejectArtifact(artifact.id);
      if (response.success && onReject) {
        onReject(artifact.id);
        // Update local state to reflect rejection
        setArtifact(prev => prev ? {...prev, status: 'rejected'} : null);
      }
    } catch (err) {
      setError('Failed to reject artifact');
      console.error('Rejection error:', err);
    } finally {
      setLoading(false);
    }
  };

  const renderArtifactContent = () => {
    if (!artifact) return null;
    
    switch (artifact.type) {
      case 'code':
        return <CodeViewer content={artifact.content} language="javascript" />;
      case 'markdown':
        return <MarkdownViewer content={artifact.content} />;
      case 'image':
        return <ImageViewer src={artifact.content} alt="Artifact image" />;
      default:
        return (
          <div style={{ padding: '16px', color: '#999' }}>
            Unsupported artifact type: {artifact.type}
          </div>
        );
    }
  };

  const renderStatus = () => {
    if (loading) {
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#666' }}>
          <Loader2 size={16} className="animate-spin" />
          Processing...
        </div>
      );
    }

    if (error) {
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ef4444' }}>
          <AlertCircle size={16} />
          {error}
        </div>
      );
    }

    if (!artifact) return null;

    switch (artifact.status) {
      case 'approved':
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#10b981' }}>
            <Check size={16} />
            Approved
          </div>
        );
      case 'rejected':
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ef4444' }}>
            <X size={16} />
            Rejected
          </div>
        );
      case 'error':
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ef4444' }}>
            <AlertCircle size={16} />
            Error loading artifact
          </div>
        );
      default:
        return null;
    }
  };

  // Handle initial loading state
  if (!artifact && loading) {
    return (
      <div style={{ 
        border: '1px solid #333', 
        borderRadius: '8px', 
        overflow: 'hidden',
        backgroundColor: '#0a0a0a'
      }}>
        <div style={{ 
          padding: '12px 16px', 
          borderBottom: '1px solid #333', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center' 
        }}>
          <div style={{ 
            fontSize: '14px', 
            fontWeight: 500,
            color: '#e5e5e5'
          }}>
            Loading Artifact...
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#666' }}>
            <Loader2 size={16} className="animate-spin" />
            Loading...
          </div>
        </div>
        
        <div style={{ 
          minHeight: '200px', 
          maxHeight: '400px', 
          overflow: 'auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <Loader2 size={32} className="animate-spin" style={{ color: '#666' }} />
        </div>
      </div>
    );
  }

  // Handle error state
  if (error) {
    return (
      <div style={{ 
        border: '1px solid #333', 
        borderRadius: '8px', 
        overflow: 'hidden',
        backgroundColor: '#0a0a0a'
      }}>
        <div style={{ 
          padding: '12px 16px', 
          borderBottom: '1px solid #333', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center' 
        }}>
          <div style={{ 
            fontSize: '14px', 
            fontWeight: 500,
            color: '#e5e5e5'
          }}>
            Artifact Error
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ef4444' }}>
            <AlertCircle size={16} />
            Error
          </div>
        </div>
        
        <div style={{ 
          minHeight: '200px', 
          maxHeight: '400px', 
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          color: '#999'
        }}>
          <AlertCircle size={32} style={{ color: '#ef4444' }} />
          <div>{error}</div>
        </div>
      </div>
    );
  }

  // If no artifact and no error, show empty state
  if (!artifact) {
    return (
      <div style={{ 
        border: '1px solid #333', 
        borderRadius: '8px', 
        overflow: 'hidden',
        backgroundColor: '#0a0a0a'
      }}>
        <div style={{ 
          padding: '12px 16px', 
          borderBottom: '1px solid #333', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center' 
        }}>
          <div style={{ 
            fontSize: '14px', 
            fontWeight: 500,
            color: '#e5e5e5'
          }}>
            No Artifact
          </div>
        </div>
        
        <div style={{ 
          minHeight: '200px', 
          maxHeight: '400px', 
          overflow: 'auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#999'
        }}>
          No artifact data available
        </div>
      </div>
    );
  }

  return (
    <div style={{ 
      border: '1px solid #333', 
      borderRadius: '8px', 
      overflow: 'hidden',
      backgroundColor: '#0a0a0a'
    }}>
      <div style={{ 
        padding: '12px 16px', 
        borderBottom: '1px solid #333', 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center' 
      }}>
        <div style={{ 
          fontSize: '14px', 
          fontWeight: 500,
          color: '#e5e5e5'
        }}>
          {artifact.type.charAt(0).toUpperCase() + artifact.type.slice(1)} Artifact
        </div>
        {renderStatus()}
      </div>
      
      <div style={{ minHeight: '200px', maxHeight: '400px', overflow: 'auto' }}>
        {artifact.status === 'loading' ? (
          <div style={{
            height: '200px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Loader2 size={32} className="animate-spin" style={{ color: '#666' }} />
          </div>
        ) : artifact.status === 'error' ? (
          <div style={{
            height: '200px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            color: '#999'
          }}>
            <AlertCircle size={32} style={{ color: '#ef4444' }} />
            <div>Failed to load artifact</div>
          </div>
        ) : (
          renderArtifactContent()
        )}
      </div>
      
      {artifact.status === 'pending' && (
        <div style={{ 
          padding: '12px 16px', 
          borderTop: '1px solid #333', 
          display: 'flex', 
          gap: '8px',
          justifyContent: 'flex-end'
        }}>
          <button
            onClick={handleReject}
            disabled={loading}
            style={{
              padding: '6px 12px',
              borderRadius: '4px',
              border: '1px solid #ef4444',
              backgroundColor: 'transparent',
              color: '#ef4444',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '14px'
            }}
          >
            <X size={16} />
            Reject
          </button>
          <button
            onClick={handleApprove}
            disabled={loading}
            style={{
              padding: '6px 12px',
              borderRadius: '4px',
              border: '1px solid #10b981',
              backgroundColor: 'transparent',
              color: '#10b981',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '14px'
            }}
          >
            <Check size={16} />
            Approve
          </button>
        </div>
      )}
    </div>
  );
}