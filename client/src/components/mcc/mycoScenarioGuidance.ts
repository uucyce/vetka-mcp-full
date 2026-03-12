export interface MycoScenarioGuidanceInput {
  navLevel?: string | null;
  nodeKind?: string | null;
  graphKind?: string | null;
  label?: string | null;
  role?: string | null;
  workflowFamily?: string | null;
  taskDrillExpanded?: boolean;
  workflowNodeContext?: boolean;
  nodeUnfoldExpanded?: boolean;
  windowFocus?: string | null;
  windowFocusState?: string | null;
  taskStatus?: string | null;
  selectedTaskId?: string | null;
  selectedNodeId?: string | null;
}

export interface MycoScenarioGuidanceResult {
  scenarioKey: string;
  topHint: string;
  chatReply: string;
}

function normalize(value: string | null | undefined): string {
  return String(value || '').trim().toLowerCase();
}

function buildWorkflowStatusAction(taskStatus: string): { short: string; long: string } {
  return taskStatus === 'running'
    ? {
        short: 'monitor Stats/stream',
        long: 'monitor Stats/stream -> wait verify/eval gate -> retry only on fail',
      }
    : taskStatus === 'done'
      ? {
          short: 'review artifacts -> pick next queued/pending task in Tasks or targeted retry',
          long: 'inspect artifacts/result -> pick next queued/pending task in Tasks, else run targeted retry',
        }
      : taskStatus === 'failed'
        ? {
            short: 'inspect failure in Context -> retry with corrected model/prompt',
            long: 'open Context -> inspect failure cause -> retry from Tasks with corrected model/prompt',
          }
        : {
            short: 'start/retry from Tasks',
            long: 'start from Tasks -> then inspect Context/stream and iterate',
          };
}

function buildWorkflowFamilyHints(workflowFamily: string): { short: string; long: string } {
  return workflowFamily === 'dragons'
    ? { short: 'team: Dragons (faster/cheaper)', long: 'Dragons: faster + cheaper' }
    : workflowFamily === 'titans'
      ? { short: 'team: Titans (smarter/costlier)', long: 'Titans: smarter + costlier' }
      : workflowFamily === 'g3'
        ? { short: 'team: G3 critic+coder', long: 'G3: critic + coder' }
        : workflowFamily === 'ralph_loop'
          ? { short: 'team: Ralph loop (single-agent)', long: 'Ralph loop: single-agent' }
          : workflowFamily
            ? { short: `team: ${workflowFamily}`, long: `${workflowFamily} workflow` }
            : { short: '', long: 'BMAD/default workflow' };
}

function buildWorkflowRoleGuidance(params: {
  role: string;
  label: string;
  kind: string;
  familyShort: string;
  familyLong: string;
  statusShort: string;
  statusLong: string;
}): { topHint: string; chatReply: string } {
  const { role, label, kind, familyShort, familyLong, statusShort, statusLong } = params;
  const labelLow = label.toLowerCase();
  const topFamily = familyShort ? ` • ${familyShort}` : '';
  const chatFamily = familyLong ? ` (${familyLong})` : '';
  if (role === 'architect') {
    return {
      topHint: `architect: refine subtasks/team preset${topFamily} • ${statusShort}`,
      chatReply: `workflow is open; architect selected${chatFamily}\n- next: define/adjust subtasks -> choose team preset (Dragons/Titans/G3/Ralph) -> ${statusLong}`,
    };
  }
  if (role === 'scout') {
    return {
      topHint: `scout: inspect impacted files/deps • hand findings to coder/architect • ${statusShort}`,
      chatReply: `workflow is open; scout selected${chatFamily}\n- next: inspect impacted files/deps in Context -> map code surface -> hand findings to coder/architect -> ${statusLong}`,
    };
  }
  if (role === 'researcher') {
    return {
      topHint: `researcher: inspect docs/constraints • hand findings to coder/architect • ${statusShort}`,
      chatReply: `workflow is open; researcher selected${chatFamily}\n- next: inspect docs/web evidence -> confirm approach/constraints -> hand findings to coder/architect -> ${statusLong}`,
    };
  }
  if (role === 'coder') {
    return {
      topHint: `coder: open Context model/prompt • ${statusShort}`,
      chatReply: `coder selected${chatFamily}\n- next: open Context -> verify model/prompt -> ${statusLong}`,
    };
  }
  if (role === 'verifier') {
    return {
      topHint: `verifier: inspect acceptance criteria • ${statusShort}`,
      chatReply: `verifier selected${chatFamily}\n- next: inspect acceptance criteria in Context -> verify code/output completeness -> ${statusLong}`,
    };
  }
  if (role === 'eval') {
    return {
      topHint: `eval: inspect score/quality signals • ${statusShort}`,
      chatReply: `eval selected${chatFamily}\n- next: inspect score/quality signals -> compare result vs target -> ${statusLong}`,
    };
  }
  if (kind === 'condition' || labelLow.includes('quality')) {
    return {
      topHint: `quality gate: decide retry vs approval • ${statusShort}`,
      chatReply: `quality gate selected${chatFamily}\n- next: inspect verifier/eval inputs -> decide retry vs approval path -> ${statusLong}`,
    };
  }
  if (labelLow.includes('approval')) {
    return {
      topHint: `approval gate: approve deploy or send back • ${statusShort}`,
      chatReply: `approval gate selected${chatFamily}\n- next: review release decision -> approve deploy or send back to coder -> ${statusLong}`,
    };
  }
  if (labelLow.includes('deploy')) {
    return {
      topHint: `deploy: verify approval/release target • ${statusShort}`,
      chatReply: `deploy step selected${chatFamily}\n- next: verify approval passed -> confirm release target -> ${statusLong}`,
    };
  }
  if (labelLow.includes('measure')) {
    return {
      topHint: `measure: inspect telemetry/test output • ${statusShort}`,
      chatReply: `measure step selected${chatFamily}\n- next: inspect telemetry/test output -> feed verifier/eval -> ${statusLong}`,
    };
  }
  return {
    topHint: familyShort
      ? `workflow open: inspect Context/model${topFamily} • ${statusShort}`
      : `workflow open: inspect Context/model • ${statusShort}`,
    chatReply: `workflow is open and agent ${role || label} is selected${chatFamily}\n- next: open Context -> check model/prompt -> ${statusLong}`,
  };
}

// MARKER_164.P5.P5.MYCO.SHARED_SCENARIO_RESOLVER.V1:
// Top hint and chat must resolve from the same scenario chain: roadmap -> task -> workflow -> agent -> run/retry.
export function resolveMycoScenarioGuidance(input: MycoScenarioGuidanceInput): MycoScenarioGuidanceResult {
  const navLevel = normalize(input.navLevel || 'roadmap') || 'roadmap';
  const nodeKind = normalize(input.nodeKind || 'project') || 'project';
  const graphKind = normalize(input.graphKind);
  const label = String(input.label || 'project');
  const role = normalize(input.role);
  const workflowFamily = normalize(input.workflowFamily);
  const taskDrillExpanded = Boolean(input.taskDrillExpanded);
  const workflowNodeContext = Boolean(input.workflowNodeContext);
  const nodeUnfoldExpanded = Boolean(input.nodeUnfoldExpanded);
  const windowFocus = normalize(input.windowFocus);
  const windowFocusState = normalize(input.windowFocusState);
  const taskStatus = normalize(input.taskStatus);
  const selectedTaskId = String(input.selectedTaskId || '');
  const selectedNodeId = String(input.selectedNodeId || '');
  const scopeLine = `you are in ${navLevel} view`;
  const inWorkflow = navLevel === 'workflow' || taskDrillExpanded || workflowNodeContext;
  const familyHints = buildWorkflowFamilyHints(workflowFamily);
  const statusHints = buildWorkflowStatusAction(taskStatus);

  if (windowFocus === 'balance') {
    const body = windowFocusState === 'expanded'
      ? 'Balance fullscreen: set active key ★ • verify provider/model • check cost/in-out'
      : 'Balance focused: set active key ★ • verify provider/model • check cost/in-out';
    return { scenarioKey: 'window_balance', topHint: body, chatReply: `MYCO\n- ${scopeLine}\n- Balance window ${windowFocusState || 'focused'}\n- next: choose active API key (★) -> verify provider/model -> check cost/in-out before run` };
  }
  if (windowFocus === 'stats') {
    const body = windowFocusState === 'expanded'
      ? 'Stats fullscreen: inspect scope/diagnostics • check runs/success/cost • open related context'
      : 'Stats focused: inspect scope/diagnostics • check runs/success/cost';
    return { scenarioKey: 'window_stats', topHint: body, chatReply: `MYCO\n- ${scopeLine}\n- Stats window ${windowFocusState || 'focused'}\n- next: inspect scope/diagnostics -> verify success/cost -> then adjust task or model` };
  }
  if (windowFocus === 'tasks') {
    const body = windowFocusState === 'expanded'
      ? 'Tasks fullscreen: pick active task • start/stop/retry • use heartbeat cadence'
      : 'Tasks focused: pick active task • start/stop/retry';
    return { scenarioKey: 'window_tasks', topHint: body, chatReply: `MYCO\n- ${scopeLine}\n- Tasks window ${windowFocusState || 'focused'}\n- next: select active task -> start/stop/retry -> monitor status + heartbeat` };
  }
  if (windowFocus === 'context') {
    const body = windowFocusState === 'expanded'
      ? 'Context fullscreen: inspect node/task details • model/prompt • stream/artifacts'
      : 'Context focused: inspect node/task details • model/prompt';
    return { scenarioKey: 'window_context', topHint: body, chatReply: `MYCO\n- ${scopeLine}\n- Context window ${windowFocusState || 'focused'}\n- next: inspect role/model/prompt -> switch model if needed -> then run from Tasks` };
  }
  if (windowFocus === 'chat') {
    const body = windowFocusState === 'expanded'
      ? 'Chat fullscreen: ask architect for plan • use current context • execute from Tasks'
      : 'Chat focused: ask architect for next step from current context';
    return { scenarioKey: 'window_chat', topHint: body, chatReply: `MYCO\n- ${scopeLine}\n- Chat window ${windowFocusState || 'focused'}\n- next: ask for concrete next steps on current node/task -> execute from Tasks` };
  }

  if (taskDrillExpanded || workflowNodeContext) {
    if (nodeKind === 'agent' || nodeKind === 'condition' || label.toLowerCase().includes('quality') || label.toLowerCase().includes('approval') || label.toLowerCase().includes('deploy') || label.toLowerCase().includes('measure')) {
      const roleGuidance = buildWorkflowRoleGuidance({
        role,
        label,
        kind: nodeKind,
        familyShort: familyHints.short,
        familyLong: familyHints.long,
        statusShort: statusHints.short,
        statusLong: statusHints.long,
      });
      return { scenarioKey: `workflow_role_${role || nodeKind || 'node'}`, topHint: roleGuidance.topHint, chatReply: `MYCO\n- ${scopeLine}\n- ${roleGuidance.chatReply}` };
    }
    if (nodeKind === 'task' || graphKind === 'project_task') {
      const topHint = familyHints.short
        ? `workflow opened: select agent node • ${familyHints.short} • ${statusHints.short}`
        : `workflow opened: select agent node • open Context • ${statusHints.short}`;
      return { scenarioKey: 'workflow_task', topHint, chatReply: `MYCO\n- ${scopeLine}\n- task is active and workflow opened (${familyHints.long})\n- next: select agent node -> open Context -> ${statusHints.long}` };
    }
    const topHint = familyHints.short
      ? `workflow opened: select agent node • ${familyHints.short} • ${statusHints.short}`
      : `workflow opened: select agent node • open Context • ${statusHints.short}`;
    return { scenarioKey: 'workflow_open', topHint, chatReply: `MYCO\n- ${scopeLine}\n- workflow is already open for the active task (${familyHints.long})\n- next: select an agent node -> inspect Context/stream -> ${statusHints.long}` };
  }

  if (nodeUnfoldExpanded) {
    return {
      scenarioKey: 'module_unfold',
      topHint: 'module unfolded: double-click deeper • select task • create task here',
      chatReply: `MYCO\n- ${scopeLine}\n- module unfold is active\n- next: double-click deeper -> pick code node -> create task in Tasks for this scope`,
    };
  }

  if (inWorkflow) {
    const topHint = familyHints.short
      ? `workflow context: select agent • ${familyHints.short} • check stream/artifacts`
      : 'workflow context: select agent • inspect Context • check stream/artifacts';
    return {
      scenarioKey: 'workflow_context',
      topHint,
      chatReply: `MYCO\n- ${scopeLine}\n- you are inside workflow context (${familyHints.long})\n- next: select agent -> inspect Context -> adjust model -> run/retry from Tasks`,
    };
  }

  if (!selectedTaskId && !selectedNodeId && nodeKind === 'project') {
    return {
      scenarioKey: 'project_root',
      topHint: 'roadmap context: click node to inspect links',
      chatReply: `MYCO\n- ${scopeLine}\n- this is project-level context\n- next: click a node and ask again`,
    };
  }

  if (nodeKind === 'task') {
    return {
      scenarioKey: 'roadmap_task',
      topHint: 'Press Enter to drill into workflow',
      chatReply: `MYCO\n- ${scopeLine}\n- selected task: ${label}\n- next: press Enter to open workflow`,
    };
  }

  if (nodeKind === 'agent') {
    return {
      scenarioKey: 'roadmap_agent',
      topHint: 'workflow context: open node and inspect roles',
      chatReply: `MYCO\n- ${scopeLine}\n- selected agent: ${role || label}\n- next: open Context to review model/prompt`,
    };
  }

  if (nodeKind === 'file' || nodeKind === 'directory') {
    return {
      scenarioKey: 'roadmap_code_scope',
      topHint: 'roadmap context: click node to inspect links',
      chatReply: `MYCO\n- ${scopeLine}\n- selected code scope: ${label}\n- next: inspect Context and linked tasks`,
    };
  }

  if (selectedTaskId) {
    return {
      scenarioKey: 'task_linked',
      topHint: 'task linked: open workflow or ask architect for next step',
      chatReply: `MYCO\n- ${scopeLine}\n- selected node: ${label}\n- next: ask architect or open Context`,
    };
  }

  return {
    scenarioKey: 'roadmap_generic',
    topHint: 'select node • create task • run workflow',
    chatReply: `MYCO\n- ${scopeLine}\n- selected node: ${label}\n- next: ask architect or open Context`,
  };
}
