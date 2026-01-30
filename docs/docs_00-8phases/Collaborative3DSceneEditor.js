// Real-time collaborative 3D scene editor with WebSocket, WebRTC, and Three.js
import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.168.0/build/three.module.js';

// Scene setup
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);
camera.position.z = 10;

// WebSocket for real-time collaboration
const ws = new WebSocket('wss://your-websocket-server'); // Replace with actual server URL
const userId = Math.random().toString(36).substring(2, 15); // Unique user ID
const userCursors = new Map(); // Store other users' cursors
let userColor = new THREE.Color(Math.random(), Math.random(), Math.random());

// Sample scene objects (nodes)
const nodes = [];
const nodeCount = 100;
for (let i = 0; i < nodeCount; i++) {
  const geometry = new THREE.SphereGeometry(0.2, 16, 16);
  const material = new THREE.MeshBasicMaterial({ color: 0x888888 });
  const sphere = new THREE.Mesh(geometry, material);
  sphere.position.set(
    (Math.random() - 0.5) * 10,
    (Math.random() - 0.5) * 10,
    (Math.random() - 0.5) * 10
  );
  sphere.userData = { id: `node-${i}`, lockedBy: null };
  nodes.push(sphere);
  scene.add(sphere);
}

// User cursor (3D sphere)
const cursorGeometry = new THREE.SphereGeometry(0.1, 16, 16);
const cursorMaterial = new THREE.MeshBasicMaterial({ color: userColor });
const cursor = new THREE.Mesh(cursorGeometry, cursorMaterial);
scene.add(cursor);

// WebSocket message handling
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'join', userId, color: userColor.getHex() }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case 'cursorUpdate':
      updateUserCursor(data.userId, data.position, data.color);
      break;
    case 'nodeUpdate':
      updateNode(data.nodeId, data.position, data.userId);
      break;
    case 'lockNode':
      lockNode(data.nodeId, data.userId);
      break;
    case 'unlockNode':
      unlockNode(data.nodeId);
      break;
  }
};

// Update other users' cursors
function updateUserCursor(userId, position, color) {
  if (!userCursors.has(userId)) {
    const geometry = new THREE.SphereGeometry(0.1, 16, 16);
    const material = new THREE.MeshBasicMaterial({ color });
    const cursorMesh = new THREE.Mesh(geometry, material);
    userCursors.set(userId, cursorMesh);
    scene.add(cursorMesh);
  }
  const cursorMesh = userCursors.get(userId);
  cursorMesh.position.set(position.x, position.y, position.z);
}

// Node update with conflict resolution
function updateNode(nodeId, position, userId) {
  const node = nodes.find(n => n.userData.id === nodeId);
  if (node && (node.userData.lockedBy === null || node.userData.lockedBy === userId)) {
    node.position.set(position.x, position.y, position.z);
  }
}

function lockNode(nodeId, userId) {
  const node = nodes.find(n => n.userData.id === nodeId);
  if (node && node.userData.lockedBy === null) {
    node.userData.lockedBy = userId;
    node.material.color.set(0xff0000); // Indicate lock
  }
}

function unlockNode(nodeId) {
  const node = nodes.find(n => n.userData.id === nodeId);
  if (node) {
    node.userData.lockedBy = null;
    node.material.color.set(0x888888);
  }
}

// WebRTC for spatial audio
const audioContext = new (window.AudioContext || window.webkitAudioContext)();
const panner = audioContext.createPanner();
panner.panningModel = 'HRTF';
panner.distanceModel = 'inverse';
panner.refDistance = 1;
panner.maxDistance = 100;
panner.rolloffFactor = 1;
const source = audioContext.createBufferSource();
fetch('https://your-audio-file.mp3') // Replace with actual audio URL
  .then(response => response.arrayBuffer())
  .then(buffer => audioContext.decodeAudioData(buffer))
  .then(decoded => {
    source.buffer = decoded;
    source.connect(panner).connect(audioContext.destination);
    source.loop = true;
    source.start();
  });

// Mouse interaction for cursor and node manipulation
let selectedNode = null;
document.addEventListener('mousemove', (event) => {
  const mouse = new THREE.Vector2(
    (event.clientX / window.innerWidth) * 2 - 1,
    -(event.clientY / window.innerHeight) * 2 + 1
  );
  const raycaster = new THREE.Raycaster();
  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(nodes);
  
  cursor.position.copy(raycaster.ray.origin).add(raycaster.ray.direction.multiplyScalar(5));
  ws.send(JSON.stringify({
    type: 'cursorUpdate',
    userId,
    position: cursor.position,
    color: userColor.getHex()
  }));

  if (intersects.length > 0 && !selectedNode) {
    selectedNode = intersects[0].object;
    if (selectedNode.userData.lockedBy === null) {
      ws.send(JSON.stringify({ type: 'lockNode', nodeId: selectedNode.userData.id, userId }));
    }
  }
});

document.addEventListener('click', () => {
  if (selectedNode && selectedNode.userData.lockedBy === userId) {
    selectedNode.position.copy(cursor.position);
    ws.send(JSON.stringify({
      type: 'nodeUpdate',
      nodeId: selectedNode.userData.id,
      position: selectedNode.position,
      userId
    }));
    ws.send(JSON.stringify({ type: 'unlockNode', nodeId: selectedNode.userData.id }));
    selectedNode = null;
  }
});

// Animation loop
function animate() {
  requestAnimationFrame(animate);
  // Update spatial audio panner based on cursor position
  panner.setPosition(cursor.position.x, cursor.position.y, cursor.position.z);
  renderer.render(scene, camera);
}
animate();

// Handle window resize
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});