import React, { useEffect } from 'react';
import { useStore } from '../store/useStore';

interface NodeInspectorProps {
  nodeId: string | null;
}

// Hidden debug-only component. Intentionally not mounted in production UI.
const NodeInspector: React.FC<NodeInspectorProps> = ({ nodeId }) => {
  const {
    nodes,
    selectedId,
    hoveredId,
    highlightedIds,
    selectNode,
    hoverNode,
    highlightNodes,
    clearHighlights
  } = useStore();

  // When nodeId prop changes, update the store
  useEffect(() => {
    if (nodeId) {
      selectNode(nodeId);
    } else {
      selectNode(null);
    }
  }, [nodeId, selectNode]);

  // Get the current node data
  const currentNode = nodeId ? nodes[nodeId] : null;

  // Handle mouse events for highlighting
  const handleMouseEnter = (id: string) => {
    hoverNode(id);
    highlightNodes([id]);
  };

  const handleMouseLeave = () => {
    hoverNode(null);
    clearHighlights();
  };

  if (!currentNode) {
    return (
      <div className="node-inspector" style={{ padding: '10px', backgroundColor: '#f5f5f5', border: '1px solid #ddd' }}>
        <p>No node selected</p>
      </div>
    );
  }

  return (
    <div 
      className="node-inspector" 
      style={{ 
        padding: '10px', 
        backgroundColor: '#f5f5f5', 
        border: '1px solid #ddd',
        minHeight: '200px'
      }}
      onMouseEnter={() => handleMouseEnter(currentNode.id)}
      onMouseLeave={handleMouseLeave}
    >
      <h3>Node Details</h3>
      <div>
        <strong>ID:</strong> {currentNode.id}<br />
        <strong>Name:</strong> {currentNode.name}<br />
        <strong>Type:</strong> {currentNode.type}<br />
        <strong>Backend Type:</strong> {currentNode.backendType}<br />
        <strong>Path:</strong> {currentNode.path}<br />
        <strong>Depth:</strong> {currentNode.depth}<br />
        {currentNode.extension && (
          <>
            <strong>Extension:</strong> {currentNode.extension}<br />
          </>
        )}
        {currentNode.semanticPosition && (
          <>
            <strong>Semantic Position:</strong><br />
            <span>  X: {currentNode.semanticPosition.x.toFixed(2)}</span><br />
            <span>  Y: {currentNode.semanticPosition.y.toFixed(2)}</span><br />
            <span>  Z: {currentNode.semanticPosition.z.toFixed(2)}</span><br />
            <span>  Knowledge Level: {currentNode.semanticPosition.knowledgeLevel}</span><br />
          </>
        )}
        {currentNode.metadata && (
          <>
            <strong>Metadata:</strong><br />
            {currentNode.metadata.chat_id && <span>Chat ID: {currentNode.metadata.chat_id}<br /></span>}
            {currentNode.metadata.message_count && <span>Message Count: {currentNode.metadata.message_count}<br /></span>}
            {currentNode.metadata.participants && (
              <span>Participants: {currentNode.metadata.participants.join(', ')}<br /></span>
            )}
          </>
        )}
      </div>
      
      {/* Visual indicators for selection/hover/highlight */}
      <div style={{ marginTop: '10px', fontSize: '12px' }}>
        <div>Selected: {selectedId === currentNode.id ? '✓' : '✗'}</div>
        <div>Hovered: {hoveredId === currentNode.id ? '✓' : '✗'}</div>
        <div>Highlighted: {highlightedIds.has(currentNode.id) ? '✓' : '✗'}</div>
      </div>
    </div>
  );
};

export default NodeInspector;
