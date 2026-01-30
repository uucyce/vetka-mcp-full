// WebGL-based neural network visualization with ONNX.js and Three.js
import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.168.0/build/three.module.js';
import * as ONNX from 'https://cdn.jsdelivr.net/npm/onnxjs@0.1.9/dist/onnx.min.js';

// Scene setup
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);
camera.position.z = 20;

// Sample neural network structure (simplified transformer)
const layers = [
  { nodes: 64, type: 'input' }, // Input layer
  { nodes: 128, type: 'attention' }, // Transformer attention layer
  { nodes: 64, type: 'dense' }, // Dense layer
  { nodes: 10, type: 'output' } // Output layer
];

// Node and edge data
const nodePositions = [];
const nodeColors = new Float32Array(layers.reduce((sum, layer) => sum + layer.nodes, 0) * 3);
const edges = [];

// Layout nodes in 3D space
let nodeIndex = 0;
layers.forEach((layer, layerIdx) => {
  const z = layerIdx * 5 - (layers.length - 1) * 2.5;
  for (let i = 0; i < layer.nodes; i++) {
    const x = (Math.random() - 0.5) * 4;
    const y = (Math.random() - 0.5) * 4;
    nodePositions.push(x, y, z);
    nodeColors[nodeIndex * 3] = layer.type === 'attention' ? 1.0 : 0.5; // Red for attention
    nodeColors[nodeIndex * 3 + 1] = 0.5;
    nodeColors[nodeIndex * 3 + 2] = layer.type === 'output' ? 1.0 : 0.5; // Blue for output
    nodeIndex++;
  }
});

// Create edges between layers
let offset = 0;
for (let l = 0; l < layers.length - 1; l++) {
  for (let i = 0; i < layers[l].nodes; i++) {
    for (let j = 0; j < layers[l + 1].nodes; j++) {
      if (Math.random() < 0.1) { // Sparse connections for visualization
        edges.push(offset + i, offset + layers[l].nodes + j);
      }
    }
  }
  offset += layers[l].nodes;
}

// WebGL geometry for nodes
const geometry = new THREE.BufferGeometry();
geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(nodePositions), 3));
geometry.setAttribute('color', new THREE.BufferAttribute(nodeColors, 3));
const material = new THREE.PointsMaterial({ size: 0.2, vertexColors: true });
const points = new THREE.Points(geometry, material);
scene.add(points);

// Edges
const edgeGeometry = new THREE.BufferGeometry();
const edgePositions = new Float32Array(edges.length * 3);
for (let i = 0; i < edges.length; i += 2) {
  const src = edges[i], dst = edges[i + 1];
  edgePositions[i * 3] = nodePositions[src * 3];
  edgePositions[i * 3 + 1] = nodePositions[src * 3 + 1];
  edgePositions[i * 3 + 2] = nodePositions[src * 3 + 2];
  edgePositions[i * 3 + 3] = nodePositions[dst * 3];
  edgePositions[i * 3 + 4] = nodePositions[dst * 3 + 1];
  edgePositions[i * 3 + 5] = nodePositions[dst * 3 + 2];
}
edgeGeometry.setAttribute('position', new THREE.BufferAttribute(edgePositions, 3));
const edgeMaterial = new THREE.LineBasicMaterial({ color: 0x888888 });
const lines = new THREE.LineSegments(edgeGeometry, edgeMaterial);
scene.add(lines);

// ONNX.js model inference
async function runInference() {
  const session = new ONNX.InferenceSession();
  await session.loadModel('https://your-model.onnx'); // Replace with actual ONNX model URL
  const inputTensor = new ONNX.Tensor(new Float32Array(64).fill(1.0), 'float32', [1, 64]);
  const outputMap = await session.run([inputTensor]);
  const output = outputMap.values().next().value.data;
  
  // Visualize output by scaling node sizes
  const sizes = new Float32Array(nodePositions.length / 3);
  for (let i = 0; i < layers[layers.length - 1].nodes; i++) {
    sizes[offset - layers[layers.length - 1].nodes + i] = output[i] * 0.5 + 0.1;
  }
  geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
  material.sizeAttenuation = true;
  geometry.attributes.size.needsUpdate = true;
}

// Transformer attention visualization
function visualizeAttention() {
  const attentionLayer = layers.find(layer => layer.type === 'attention');
  const attentionOffset = layers.slice(0, layers.indexOf(attentionLayer)).reduce((sum, l) => sum + l.nodes, 0);
  for (let i = 0; i < attentionLayer.nodes; i++) {
    // Simulate attention weights (random for demo)
    const weight = Math.random();
    nodeColors[(attentionOffset + i) * 3] = weight; // Red channel for attention weight
  }
  geometry.attributes.color.needsUpdate = true;
}

// Animation loop
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
runInference();
visualizeAttention();

// Handle window resize
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});