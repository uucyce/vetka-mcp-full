import React, { useEffect, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';

// MARKER_102.1_START
const UnifiedSearchBar: React.FC<{ onSearch: (query: string) => void }> = ({ onSearch }) => {
  const [query, setQuery] = useState('');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(query);
  };

  return (
    <form 
      onSubmit={handleSubmit}
      style={{
        position: 'fixed',
        top: '16px',
        left: '50%',
        transform: 'translateX(-50%)',
        width: '50vw',
        minWidth: '400px',
        zIndex: 1000,
        display: 'flex',
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        overflow: 'hidden'
      }}
    >
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
        style={{
          flex: 1,
          padding: '12px 16px',
          border: 'none',
          outline: 'none',
          fontSize: '16px'
        }}
      />
      <button 
        type="submit"
        style={{
          padding: '12px 20px',
          backgroundColor: '#007AFF',
          color: 'white',
          border: 'none',
          cursor: 'pointer',
          fontWeight: '600'
        }}
      >
        Search
      </button>
    </form>
  );
};
// MARKER_102.1_END

const App: React.FC = () => {
  // ... rest of the component
};