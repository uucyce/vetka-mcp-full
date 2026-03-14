# PHASE 177 — Roadmap <-> TaskBoard sync proposal

Date: 2026-03-12
Status: proposal
Tag: `localguys`, `roadmap`, `taskboard`, `sync`

## Problem
Roadmap and TaskBoard still behave like two related but partially separate systems.
That creates duplicated planning work and weak agent context.

## Desired end state
Roadmap is the strategic graph.
TaskBoard is the operational execution surface.
MCC binds them so an agent receives a task packet, not just a task title.

## Required task packet
Any task dispatched through MCC/localguys should be able to carry:
- task metadata
- roadmap node binding
- workflow family binding
- team/profile binding
- primary docs
- code scope
- suggested tests
- artifact history
- failure history / feedback

## Proposal
### 1. Roadmap node binding becomes first-class
Each TaskBoard task should optionally store:
- `roadmap_id`
- `roadmap_node_id`
- `roadmap_lane`
- `roadmap_title`

### 2. Context packet endpoint
Add a machine-readable task packet endpoint that resolves:
- task fields
- workflow contract
- roadmap binding
- doc links
- likely code scope
- likely tests
- recent artifacts

### 3. Roadmap -> TaskBoard generator
Promote roadmap node expansion into a formal tool path:
- roadmap node -> task templates
- task templates -> TaskBoard entries
- preserve binding metadata for later agent context

### 4. TaskBoard -> roadmap progress sync
Task completion and verifier outcome should update roadmap execution status.

## Why this helps localguys
If this exists, a local agent run can start from a structured packet instead of ad hoc file hunting.
That reduces recon drift and closes the gap between roadmap planning and task execution.

## Success criteria
- one roadmap node can generate task pack(s)
- one TaskBoard task can reconstruct its roadmap/doc/test context packet
- MCC/localguys consume the same packet shape
