// MARKER_102.2_START
const TopRightButtons = () => {
  const { 
    showChat, 
    showArtifact, 
    showMCC, 
    toggleChat, 
    toggleArtifact, 
    toggleMCC 
  } = useStore(s => ({
    showChat: s.showChat,
    showArtifact: s.showArtifact,
    showMCC: s.showMCC,
    toggleChat: s.toggleChat,
    toggleArtifact: s.toggleArtifact,
    toggleMCC: s.toggleMCC,
  }));

  return (
    <div 
      style={{
        position: 'absolute',
        top: '16px',
        right: '16px',
        display: 'flex',
        flexDirection: 'row',
        gap: '8px',
        zIndex: 1000,
      }}
    >
      <button
        onClick={toggleChat}
        style={{
          background: showChat ? 'rgba(59, 130, 246, 0.8)' : 'rgba(255, 255, 255, 0.8)',
          border: 'none',
          borderRadius: '8px',
          padding: '8px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}
      >
        <MessageSquare size={20} color={showChat ? 'white' : 'black'} />
      </button>
      
      <button
        onClick={toggleArtifact}
        style={{
          background: showArtifact ? 'rgba(59, 130, 246, 0.8)' : 'rgba(255, 255, 255, 0.8)',
          border: 'none',
          borderRadius: '8px',
          padding: '8px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}
      >
        <TerminalSquare size={20} color={showArtifact ? 'white' : 'black'} />
      </button>
      
      <button
        onClick={toggleMCC}
        style={{
          background: showMCC ? 'rgba(59, 130, 246, 0.8)' : 'rgba(255, 255, 255, 0.8)',
          border: 'none',
          borderRadius: '8px',
          padding: '8px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}
      >
        <div style={{ 
          width: 20, 
          height: 20, 
          backgroundColor: showMCC ? 'white' : 'black',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '10px',
          fontWeight: 'bold',
          color: showMCC ? 'black' : 'white'
        }}>
          MCC
        </div>
      </button>
    </div>
  );
};
// MARKER_102.2_END