/**
 * MARKER_144.6: Workflow Toolbar — save/load/validate/execute controls.
 * Thin bar between header and DAG area, only visible in edit mode.
 * Nolan palette, monospace, compact.
 *
 * @phase 144
 * @status active
 */

import { memo, useState, useCallback, useEffect } from 'react';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { useMCCStore } from '../../store/useMCCStore';
import type { WorkflowSummary } from '../../types/dag';

interface WorkflowToolbarProps {
  // State from useDAGEditor
  workflowId: string | null;
  workflowName: string;
  isDirty: boolean;
  canUndo: boolean;
  canRedo: boolean;
  // Actions from useDAGEditor
  onNew: () => void;
  onSave: (name?: string) => Promise<string | null>;
  onLoad: (workflowId: string) => Promise<boolean>;
  onListWorkflows: () => Promise<WorkflowSummary[]>;
  onValidate: () => Promise<{ valid: boolean; errors: any[]; warnings: any[] }>;
  onUndo: () => void;
  onRedo: () => void;
  onSetName: (name: string) => void;
  // Edit mode toggle
  onToggleEdit: () => void;
  editMode: boolean;
  // MARKER_144.7: Generate workflow from description
  onGenerate?: (workflow: any) => void;
  // MARKER_144.8/9: Import/Export
  onImport?: (workflow: any) => void;
}

const btnStyle: React.CSSProperties = {
  background: 'transparent',
  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
  borderRadius: 2,
  padding: '2px 8px',
  color: NOLAN_PALETTE.textMuted,
  fontSize: 9,
  cursor: 'pointer',
  fontFamily: 'monospace',
  transition: 'background 0.1s, color 0.1s',
};

const btnActiveStyle: React.CSSProperties = {
  ...btnStyle,
  background: 'rgba(255,255,255,0.08)',
  color: NOLAN_PALETTE.text,
};

const btnDisabledStyle: React.CSSProperties = {
  ...btnStyle,
  opacity: 0.3,
  cursor: 'default',
};

const separatorStyle: React.CSSProperties = {
  width: 1,
  height: 16,
  background: NOLAN_PALETTE.borderDim,
  margin: '0 4px',
};

function WorkflowToolbarComponent({
  workflowId,
  workflowName,
  isDirty,
  canUndo,
  canRedo,
  onNew,
  onSave,
  onLoad,
  onListWorkflows,
  onValidate,
  onUndo,
  onRedo,
  onSetName,
  onToggleEdit,
  editMode,
  onGenerate,
  onImport,
}: WorkflowToolbarProps) {
  const [showLoadMenu, setShowLoadMenu] = useState(false);
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [validationMsg, setValidationMsg] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [generating, setGenerating] = useState(false);
  const executeWorkflow = useMCCStore(s => s.executeWorkflow);
  const activePreset = useMCCStore(s => s.activePreset);

  // Load workflows list when menu opens
  useEffect(() => {
    if (showLoadMenu) {
      onListWorkflows().then(setWorkflows);
    }
  }, [showLoadMenu, onListWorkflows]);

  // Clear validation message after 3s
  useEffect(() => {
    if (validationMsg) {
      const t = setTimeout(() => setValidationMsg(null), 3000);
      return () => clearTimeout(t);
    }
  }, [validationMsg]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    const name = workflowName === 'Untitled Workflow'
      ? prompt('Workflow name:', 'My Workflow') || 'My Workflow'
      : workflowName;
    onSetName(name);
    const id = await onSave(name);
    setSaving(false);
    if (id) setValidationMsg(`Saved: ${name}`);
    else setValidationMsg('Save failed');
  }, [onSave, workflowName, onSetName]);

  const handleValidate = useCallback(async () => {
    const result = await onValidate();
    if (result.valid) {
      setValidationMsg(`Valid (${result.warnings.length} warnings)`);
    } else {
      setValidationMsg(`Invalid: ${result.errors.length} errors`);
    }
  }, [onValidate]);

  // MARKER_144.10: Execute workflow — save first, then convert to tasks + dispatch
  const handleExecute = useCallback(async () => {
    if (!workflowId) {
      setValidationMsg('Save workflow first');
      return;
    }
    setExecuting(true);
    try {
      // Save if dirty
      if (isDirty) {
        await onSave(workflowName);
      }
      const result = await executeWorkflow(workflowId);
      if (result.success) {
        setValidationMsg(
          `Executed: ${result.count} tasks, ${result.tasks_dispatched?.length || 0} dispatched`
        );
      } else {
        setValidationMsg(`Execute failed: ${result.error || 'unknown'}`);
      }
    } catch (err) {
      setValidationMsg('Execute error');
    } finally {
      setExecuting(false);
    }
  }, [workflowId, isDirty, workflowName, onSave, executeWorkflow]);

  const handleLoad = useCallback(async (wfId: string) => {
    await onLoad(wfId);
    setShowLoadMenu(false);
  }, [onLoad]);

  // MARKER_144.7: Generate workflow from natural language description
  const handleGenerate = useCallback(async () => {
    const description = prompt('Describe the workflow to generate:');
    if (!description?.trim()) return;
    setGenerating(true);
    setValidationMsg('Generating...');
    try {
      const res = await fetch('http://localhost:5001/api/workflows/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: description.trim(),
          preset: activePreset,
          save: false,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.workflow) {
          setValidationMsg(
            `Generated: ${data.workflow.nodes?.length || 0} nodes (${data.model_used || 'unknown'})`
          );
          onGenerate?.(data.workflow);
        } else {
          setValidationMsg(`Generate failed: ${data.error || 'unknown'}`);
        }
      } else {
        setValidationMsg('Generate API error');
      }
    } catch (err) {
      setValidationMsg('Generate error');
    } finally {
      setGenerating(false);
    }
  }, [activePreset, onGenerate]);

  // MARKER_144.8: Import workflow from file (n8n or ComfyUI JSON)
  const handleImport = useCallback(async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e: any) => {
      const file = e.target.files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        setValidationMsg('Importing...');
        const res = await fetch('http://localhost:5001/api/workflows/import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ data, save: true }),
        });
        if (res.ok) {
          const result = await res.json();
          if (result.success && result.workflow) {
            setValidationMsg(
              `Imported ${result.format_detected}: ${result.workflow.nodes?.length || 0} nodes`
            );
            onImport?.(result.workflow);
          } else {
            setValidationMsg(`Import failed: ${result.error || 'unknown'}`);
          }
        } else {
          setValidationMsg('Import API error');
        }
      } catch (err) {
        setValidationMsg('Import error: invalid JSON');
      }
    };
    input.click();
  }, [onImport]);

  // MARKER_144.8/9: Export workflow to n8n or ComfyUI
  const [showExportMenu, setShowExportMenu] = useState(false);
  const handleExport = useCallback(async (format: 'n8n' | 'comfyui') => {
    if (!workflowId) {
      setValidationMsg('Save workflow first');
      return;
    }
    setShowExportMenu(false);
    try {
      const res = await fetch(`http://localhost:5001/api/workflows/${workflowId}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.exported) {
          // Download as JSON file
          const blob = new Blob([JSON.stringify(data.exported, null, 2)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `${workflowName || 'workflow'}_${format}.json`;
          a.click();
          URL.revokeObjectURL(url);
          setValidationMsg(`Exported as ${format}`);
        } else {
          setValidationMsg(`Export failed: ${data.error || 'unknown'}`);
        }
      }
    } catch (err) {
      setValidationMsg('Export error');
    }
  }, [workflowId, workflowName]);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        padding: '3px 10px',
        borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
        background: editMode ? 'rgba(255,255,255,0.02)' : 'transparent',
        flexShrink: 0,
        flexWrap: 'wrap',
      }}
    >
      {/* Edit mode toggle */}
      <button
        style={editMode ? btnActiveStyle : btnStyle}
        onClick={onToggleEdit}
        title={editMode ? 'Exit edit mode' : 'Enter edit mode'}
      >
        {editMode ? '✎ editing' : '✎ edit'}
      </button>

      {editMode && (
        <>
          <div style={separatorStyle} />

          {/* Workflow name */}
          <span
            style={{
              fontSize: 9,
              color: NOLAN_PALETTE.textMuted,
              maxWidth: 120,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={workflowName}
          >
            {workflowName}
            {isDirty && <span style={{ color: NOLAN_PALETTE.text }}> *</span>}
          </span>

          <div style={separatorStyle} />

          {/* New */}
          <button style={btnStyle} onClick={onNew} title="New workflow">
            New
          </button>

          {/* Save */}
          <button
            style={saving ? btnDisabledStyle : btnStyle}
            onClick={handleSave}
            title="Save workflow"
          >
            {saving ? '...' : 'Save'}
          </button>

          {/* Load dropdown */}
          <div style={{ position: 'relative' }}>
            <button
              style={btnStyle}
              onClick={() => setShowLoadMenu(!showLoadMenu)}
              title="Load workflow"
            >
              Load ▾
            </button>
            {showLoadMenu && (
              <div
                style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  zIndex: 100,
                  background: NOLAN_PALETTE.bgLight,
                  border: `1px solid ${NOLAN_PALETTE.border}`,
                  borderRadius: 3,
                  minWidth: 180,
                  maxHeight: 200,
                  overflowY: 'auto',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                }}
              >
                {workflows.length === 0 ? (
                  <div style={{ padding: 8, fontSize: 9, color: NOLAN_PALETTE.textDim }}>
                    No saved workflows
                  </div>
                ) : (
                  workflows.map(wf => (
                    <div
                      key={wf.id}
                      style={{
                        padding: '5px 10px',
                        fontSize: 9,
                        color: NOLAN_PALETTE.text,
                        cursor: 'pointer',
                        borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = NOLAN_PALETTE.bgDim)}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                      onClick={() => handleLoad(wf.id)}
                    >
                      <div style={{ fontWeight: 500 }}>{wf.name}</div>
                      <div style={{ color: NOLAN_PALETTE.textDim, fontSize: 8, marginTop: 1 }}>
                        {wf.node_count} nodes · {wf.edge_count} edges
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          <div style={separatorStyle} />

          {/* Undo / Redo */}
          <button
            style={canUndo ? btnStyle : btnDisabledStyle}
            onClick={canUndo ? onUndo : undefined}
            title="Undo (Ctrl+Z)"
          >
            ↩
          </button>
          <button
            style={canRedo ? btnStyle : btnDisabledStyle}
            onClick={canRedo ? onRedo : undefined}
            title="Redo (Ctrl+Shift+Z)"
          >
            ↪
          </button>

          <div style={separatorStyle} />

          {/* Validate */}
          <button style={btnStyle} onClick={handleValidate} title="Validate workflow">
            Validate ✓
          </button>

          {/* MARKER_144.7: AI Generate */}
          <button
            style={generating ? btnDisabledStyle : {
              ...btnStyle,
              background: 'rgba(255,255,255,0.03)',
            }}
            onClick={!generating ? handleGenerate : undefined}
            title="AI: generate workflow from description"
          >
            {generating ? '...' : '✦ Generate'}
          </button>

          {/* MARKER_144.8: Import */}
          <button
            style={btnStyle}
            onClick={handleImport}
            title="Import n8n or ComfyUI workflow JSON"
          >
            ↓ Import
          </button>

          {/* MARKER_144.8/9: Export dropdown */}
          <div style={{ position: 'relative' }}>
            <button
              style={workflowId ? btnStyle : btnDisabledStyle}
              onClick={workflowId ? () => setShowExportMenu(!showExportMenu) : undefined}
              title={workflowId ? 'Export workflow to n8n or ComfyUI' : 'Save workflow first'}
            >
              ↑ Export ▾
            </button>
            {showExportMenu && (
              <div
                style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  zIndex: 100,
                  background: NOLAN_PALETTE.bgLight,
                  border: `1px solid ${NOLAN_PALETTE.border}`,
                  borderRadius: 3,
                  minWidth: 120,
                  boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                }}
              >
                <div
                  style={{ padding: '5px 10px', fontSize: 9, color: NOLAN_PALETTE.text, cursor: 'pointer' }}
                  onMouseEnter={e => (e.currentTarget.style.background = NOLAN_PALETTE.bgDim)}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  onClick={() => handleExport('n8n')}
                >
                  n8n JSON
                </div>
                <div
                  style={{ padding: '5px 10px', fontSize: 9, color: NOLAN_PALETTE.text, cursor: 'pointer',
                    borderTop: `1px solid ${NOLAN_PALETTE.borderDim}` }}
                  onMouseEnter={e => (e.currentTarget.style.background = NOLAN_PALETTE.bgDim)}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  onClick={() => handleExport('comfyui')}
                >
                  ComfyUI JSON
                </div>
              </div>
            )}
          </div>

          <div style={separatorStyle} />

          {/* MARKER_144.10: Execute workflow */}
          <button
            style={executing || !workflowId ? btnDisabledStyle : {
              ...btnStyle,
              background: 'rgba(255,255,255,0.04)',
              color: NOLAN_PALETTE.text,
              fontWeight: 600,
            }}
            onClick={!executing && workflowId ? handleExecute : undefined}
            title={workflowId
              ? 'Execute workflow: convert to tasks + dispatch'
              : 'Save workflow first to execute'
            }
          >
            {executing ? '...' : '▶ Execute'}
          </button>

          {/* Validation message toast */}
          {validationMsg && (
            <span
              style={{
                fontSize: 8,
                color: validationMsg.startsWith('Valid') || validationMsg.startsWith('Saved')
                  ? NOLAN_PALETTE.statusDone
                  : NOLAN_PALETTE.statusFailed,
                marginLeft: 4,
              }}
            >
              {validationMsg}
            </span>
          )}
        </>
      )}
    </div>
  );
}

export const WorkflowToolbar = memo(WorkflowToolbarComponent);
