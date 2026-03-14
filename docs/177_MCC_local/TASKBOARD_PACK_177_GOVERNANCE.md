# PHASE 177 — TaskBoard pack: governance after LiteRT

These tasks start after the LiteRT lane, beginning from `tb_1773275513_7`.

## Tasks

### 1. Draft TaskBoard Governance V1
- title: `Draft TaskBoard Governance V1`
- priority: `2`
- phase_type: `research`
- workflow_family: `docs_localguys`
- tags: `localguys`, `taskboard`, `governance`, `docs`
- depends_on:
- `tb_1773275513_7`

### 2. Add minimal governance fields to TaskBoard
- title: `Add minimal governance fields to TaskBoard`
- priority: `1`
- phase_type: `build`
- workflow_family: `g3_localguys`
- tags: `localguys`, `taskboard`, `governance`, `metadata`
- depends_on:
- `tb_1773275513_7`

### 3. Enforce owner and completion contract gates
- title: `Enforce TaskBoard owner and completion contract gates`
- priority: `1`
- phase_type: `build`
- workflow_family: `g3_localguys`
- tags: `localguys`, `taskboard`, `governance`, `enforcement`
- depends_on:
- `tb_1773275513_7`

### 4. Add extended governance fields and policy matrix
- title: `Add extended TaskBoard governance fields`
- priority: `2`
- phase_type: `build`
- workflow_family: `g3_localguys`
- tags: `localguys`, `taskboard`, `governance`, `policy`
- depends_on:
- `tb_1773275513_7`

### 5. Feed governance metadata into MCC task packets
- title: `Feed TaskBoard governance metadata into MCC task packets`
- priority: `1`
- phase_type: `build`
- workflow_family: `g3_localguys`
- tags: `localguys`, `taskboard`, `governance`, `mcc`, `context-packet`
- depends_on:
- `tb_1773275513_7`
