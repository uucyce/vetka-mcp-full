import { useCallback } from 'react';
import { useMCCStore } from '../../store/useMCCStore';

interface HeartbeatToggleProps {
  className?: string;
}

export function HeartbeatToggle({ className }: HeartbeatToggleProps) {
  const { heartbeat, updateHeartbeat } = useMCCStore();
  
  const toggleHeartbeat = useCallback(async () => {
    if (!heartbeat) return;
    
    try {
      const response = await fetch('/api/debug/heartbeat/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          enabled: !heartbeat.enabled 
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          updateHeartbeat({ enabled: !heartbeat.enabled });
        }
      }
    } catch (error) {
      console.error('Failed to toggle heartbeat:', error);
    }
  }, [heartbeat, updateHeartbeat]);

  if (!heartbeat) return null;

  return (
    <button
      onClick={toggleHeartbeat}
      className={className}
      style={{
        background: heartbeat.enabled ? '#4ecdc4' : '#333',
        border: 'none',
        borderRadius: '50%',
        width: '20px',
        height: '20px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: heartbeat.enabled ? '#000' : '#fff',
        fontSize: '12px',
        transition: 'all 0.2s ease',
      }}
      title={heartbeat.enabled ? "Pause heartbeat" : "Start heartbeat"}
    >
      {heartbeat.enabled ? '●' : '○'}
    </button>
  );
}