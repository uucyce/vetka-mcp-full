// Sample Three.js implementation for rendering 10,000+ nodes with LOD and Metal-optimized WebGL
import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.168.0/build/three.module.js';

// Scene setup
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Camera position
camera.position.z = 50;

// Node data (10,000+ nodes)
const nodeCount = 10000;
const nodes = new Float32Array(nodeCount * 3); // x, y, z positions
const sizes = new Float32Array(nodeCount); // Size for LOD
const colors = new Float32Array(nodeCount * 3); // RGB colors

// Generate random node positions and attributes
for (let i = 0; i < nodeCount; i++) {
  nodes[i * 3] = (Math.random() - 0.5) * 100; // x
  nodes[i * 3 + 1] = (Math.random() - 0.5) * 100; // y
  nodes[i * 3 + 2] = (Math.random() - 0.5) * 100; // z
  sizes[i] = Math.random() * 2 + 0.5; // Random size
  colors[i * 3] = Math.random(); // R
  colors[i * 3 + 1] = Math.random(); // G
  colors[i * 3 + 2] = Math.random(); // B
}

// Instanced geometry for nodes
const geometry = new THREE.BufferGeometry();
geometry.setAttribute('position', new THREE.BufferAttribute(nodes, 3));
geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

// Shader for LOD
const vertexShader = `
  attribute float size;
  varying vec3 vColor;
  void main() {
    vColor = color;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = size * (300.0 / -mvPosition.z); // LOD: scale size by distance
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const fragmentShader = `
  varying vec3 vColor;
  void main() {
    gl_FragColor = vec4(vColor, 1.0);
  }
`;

const material = new THREE.ShaderMaterial({
  vertexShader,
  fragmentShader,
  vertexColors: true,
});

// Points for nodes
const points = new THREE.Points(geometry, material);
scene.add(points);

// Edges (simplified for demo)
const edgeGeometry = new THREE.BufferGeometry();
const edgePositions = new Float32Array(nodeCount * 6); // Lines between nodes
for (let i = 0; i < nodeCount / 2; i++) {
  edgePositions[i * 6] = nodes[i * 6];
  edgePositions[i * 6 + 1] = nodes[i * 6 + 1];
  edgePositions[i * 6 + 2] = nodes[i * 6 + 2];
  edgePositions[i * 6 + 3] = nodes[(i + 1) * 6];
  edgePositions[i * 6 + 4] = nodes[(i + 1) * 6 + 1];
  edgePositions[i * 6 + 5] = nodes[(i + 1) * 6 + 2];
}
edgeGeometry.setAttribute('position', new THREE.BufferAttribute(edgePositions, 3));
const edgeMaterial = new THREE.LineBasicMaterial({ color: 0x888888 });
const edges = new THREE.LineSegments(edgeGeometry, edgeMaterial);
scene.add(edges);

// Animation loop
function animate() {
  requestAnimationFrame(animate);
  // Update LOD based on camera distance
  const camPos = camera.position;
  for (let i = 0; i < nodeCount; i++) {
    const dist = camPos.distanceTo(new THREE.Vector3(nodes[i * 3], nodes[i * 3 + 1], nodes[i * 3 + 2]));
    sizes[i] = dist < 20 ? 2.0 : dist < 50 ? 1.0 : 0.5; // LOD levels
  }
  geometry.attributes.size.needsUpdate = true;
  renderer.render(scene, camera);
}
animate();

// Handle window resize
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});