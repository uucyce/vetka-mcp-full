# 🔧 VETKA TECHNICAL SPECIFICATIONS 2025

## HARDWARE REQUIREMENTS

### MINIMUM SPECS (2D Fallback):
- **CPU**: Any modern processor (Intel i5/AMD Ryzen 5)
- **RAM**: 4GB minimum, 8GB recommended
- **GPU**: Integrated graphics with WebGL support
- **Browser**: Chrome 100+, Safari 15+, Firefox 95+
- **Performance**: 30fps @ 1k nodes, 2D Canvas rendering

### RECOMMENDED SPECS (3D WebGL):
- **CPU**: Apple M2/Intel i7/AMD Ryzen 7
- **RAM**: 16GB for complex graphs
- **GPU**: Dedicated graphics or Apple Silicon
- **Browser**: Chrome 130+, Safari 19+, Firefox 132+
- **Performance**: 60fps @ 10k nodes, WebGL rendering

### OPTIMAL SPECS (3D WebGPU):  
- **CPU**: Apple M4 Pro/Intel i9/AMD Ryzen 9
- **RAM**: 32GB+ for massive datasets
- **GPU**: Apple M4 Pro 38-core/RTX 4080/RX 7800XT
- **Browser**: Safari 19+, Chrome 130+ (WebGPU enabled)
- **Performance**: 60fps @ 100k nodes, WebGPU + compute shaders

## SOFTWARE STACK

### BACKEND (Python):
- **Python**: 3.12+ (required for Elysia compatibility)
- **Framework**: FastAPI 0.104+ for WebSocket support
- **AI Engine**: Elysia AI v0.1.0.dev6+ (forked version)
- **Vector DB**: Weaviate v1.22+, Pinecone v2.2+, or Chroma v0.4+
- **Dependencies**: DSPy, NumPy, Pandas, AsyncIO, WebSockets

### FRONTEND (JavaScript):
- **3D Engine**: Three.js v0.168.0+ (WebGL/WebGPU)
- **Dimensionality**: UMAP.js v1.4+ for vector projection
- **Clustering**: HDBSCAN.js or server-side Python clustering
- **Communication**: Native WebSocket + WebRTC for collaboration
- **UI Framework**: Vanilla JS or lightweight framework (Alpine.js)

### DEPLOYMENT:
- **Development**: Local Python + file serving
- **Production**: Docker containers + K8s orchestration
- **CDN**: Cloudflare for Three.js and static assets
- **Database**: Cloud vector DB (Weaviate Cloud, Pinecone)
- **Monitoring**: Grafana + Prometheus for performance tracking

## API SPECIFICATIONS

### WebSocket Protocol:
```json
{
  "type": "spatial_update",
  "timestamp": 1699123456789,
  "nodes": [
    {"id": "node1", "x": 0, "y": 8.0, "z": 0, "confidence": 0.8},
    {"id": "node2", "x": 5, "y": 6.0, "z": 3, "confidence": 0.6}
  ],
  "edges": [["node1", "node2"]],
  "matryoshka_level": "nodes",
  "reasoning_path": ["step1", "step2", "conclusion"]
}
```

### REST API Endpoints:
- **POST /api/v1/query** → Submit AI query, get decision tree 
- **GET /api/v1/graph/{id}** → Retrieve spatial graph data
- **POST /api/v1/cluster** → Request clustering at specific level
- **GET /api/v1/search** → Vector similarity search
- **WebSocket /ws** → Real-time spatial updates

### Performance Benchmarks:
- **Query Processing**: <500ms from question to spatial coordinates
- **WebSocket Latency**: <50ms for real-time updates  
- **3D Rendering**: 60fps minimum for production use
- **Memory Usage**: <8GB RAM for 100k node graphs
- **Network**: <1MB/s bandwidth for real-time collaboration

## SECURITY & PRIVACY

### Data Protection:
- **Vector Embeddings**: Client-side encryption for sensitive data
- **WebSocket**: WSS (TLS encryption) for all communications
- **Authentication**: JWT tokens for user sessions
- **Privacy**: Local processing option for confidential datasets

### Performance Monitoring:
- **FPS Tracking**: Real-time frame rate monitoring
- **Memory Usage**: WebGL buffer and JavaScript heap tracking
- **Network Latency**: WebSocket round-trip time measurement
- **Error Logging**: Comprehensive error tracking and reporting

## BROWSER COMPATIBILITY MATRIX

| Feature | Chrome 130+ | Safari 19+ | Firefox 132+ | Edge 118+ |
|---------|-------------|------------|--------------|-----------|
| WebGL 2 | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| WebGPU | ✅ Full | ✅ Full | ⚠️ Limited | ✅ Full |
| WebSocket | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| WebRTC | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| WebXR | ✅ Full | ⚠️ Limited | ⚠️ Limited | ✅ Full |

### Fallback Strategy:
1. **WebGPU Available**: Use advanced compute shaders + high performance
2. **WebGL Only**: Standard 3D rendering with CPU clustering
3. **Limited GPU**: 2D fallback with Canvas + SVG
4. **No WebGL**: Text-based interface with basic visualization

