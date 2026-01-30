import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Environment, Center } from '@react-three/drei';
import { Suspense, useEffect } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import * as THREE from 'three';
import { useState } from 'react';

interface Props {
  url: string;
}

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);

  // Cleanup GPU memory on unmount or URL change
  useEffect(() => {
    return () => {
      // Dispose all materials and geometries
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry?.dispose();
          if (object.material) {
            if (Array.isArray(object.material)) {
              object.material.forEach((mat: THREE.Material) => mat.dispose());
            } else {
              object.material.dispose();
            }
          }
        }
      });

      // Clear GLTF cache for this URL
      useGLTF.clear(url);
    };
  }, [url, scene]);

  return <primitive object={scene} />;
}

function LoadingSpinner() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-vetka-bg">
      <Loader2 className="w-8 h-8 animate-spin text-vetka-muted" />
    </div>
  );
}

function ErrorDisplay({ error }: { error: string }) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-vetka-bg">
      <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
      <p className="text-vetka-text mb-2">Failed to load 3D model</p>
      <p className="text-vetka-muted text-sm">{error}</p>
    </div>
  );
}

export function ThreeDViewer({ url }: Props) {
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="relative h-full bg-vetka-bg">
      {error && <ErrorDisplay error={error} />}
      <Suspense fallback={<LoadingSpinner />}>
        <Canvas
          camera={{ position: [0, 0, 5], fov: 50 }}
          onCreated={(state) => {
            state.gl.setClearColor(0x0a0a0a, 1);
          }}
        >
          <ambientLight intensity={0.5} />
          <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} />

          <Center>
            <Model url={url} />
          </Center>

          <OrbitControls
            enableDamping
            dampingFactor={0.05}
            minDistance={1}
            maxDistance={100}
          />
          <Environment preset="city" />
        </Canvas>
      </Suspense>

      <div className="absolute bottom-4 left-4 text-xs text-vetka-muted">
        Drag to rotate • Scroll to zoom • Right-drag to pan
      </div>
    </div>
  );
}
