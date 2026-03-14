# API Endpoint Specification - MARKER_102.1

## Framework & Architecture
- **Backend**: Python FastAPI (port 5001)
- **Real-time**: SocketIO for live updates
- **Frontend**: React 18 + TypeScript + Zustand state management
- **Pattern**: RESTful endpoints + WebSocket events

## Existing API Patterns Found

### 1. Pipeline Routes (`src/api/routes/pipeline.py`)