// @ts-nocheck
/**
 * VETKA Browser Agent Bridge
 *
 * @file browserAgentBridge.ts
 * @status ACTIVE
 * @phase Phase 80.3 - MCP Agents in Model Directory
 *
 * Provides window.vetkaAPI for browser-based AI agents (like Claude in Chrome)
 * to access VETKA's debug endpoints from the browser console.
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * 🎯 QUICK START FOR NEW SESSIONS (Browser Agents read this first!)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Step 1: Run quick status check
 *   await vetkaAPI.quickStatus()
 *   → Returns: tree health, errors, components, all in one call
 *
 * Step 2: If issues found, dig deeper:
 *   - Tree unhealthy? → vetkaAPI.getTreeState()
 *   - Has errors? → vetkaAPI.getErrors()
 *   - Layout wrong? → vetkaAPI.getFormulas('mode')
 *
 * Step 3: Report findings to Claude Code (MCP) for fixes
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * 🚨 RED FLAGS (Tell Claude Code immediately):
 * ═══════════════════════════════════════════════════════════════════════════
 *   - healthy: false
 *   - status: "red"
 *   - recent_errors_count > 0
 *   - qdrant_connected: false
 *   - memory_manager_active: false
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * 📋 ALL COMMANDS:
 * ═══════════════════════════════════════════════════════════════════════════
 *   vetkaAPI.quickStatus()            - ONE COMMAND to check everything
 *   vetkaAPI.getTreeState()           - Quick health check
 *   vetkaAPI.inspect()                - Full state inspection
 *   vetkaAPI.inspect('blend')         - Filtered inspection
 *   vetkaAPI.getFormulas('knowledge') - Layout formula values
 *   vetkaAPI.getErrors()              - Recent errors
 *   vetkaAPI.getLogs()                - Debug logs
 *   vetkaAPI.getDetachedMediaSnapshot() - Latest detached media geometry
 *   vetkaAPI.getModes()               - Visualization mode info
 *   vetkaAPI.getChatContext()         - Get chat context (like internal agents)
 *   vetkaAPI.focusCamera('file.py')   - Control 3D camera!
 *   vetkaAPI.sendTeamMessage(msg)     - Send message to Claude Code! 💬
 *   vetkaAPI.readTeamMessages()       - Read incoming messages
 *   vetkaAPI.help()                   - Show all available commands
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * 🔒 REMEMBER: Code changes go through Claude Code (MCP).
 *              But you CAN control camera, read state, and send messages!
 * ═══════════════════════════════════════════════════════════════════════════
 */

const API_BASE = `${CORE_API_BASE}/debug`;

interface TreeState {
  healthy: boolean;
  collection?: string;
  files_count?: number;
  vectors_count?: number;
  error?: string;
  suggestion?: string;
}

interface InspectResult {
  timestamp: number;
  vetka_phase: string;
  qdrant_connected: boolean;
  memory_manager_active: boolean;
  layout_constants: Record<string, unknown>;
  tree_stats: Record<string, unknown>;
  modes: Record<string, unknown>;
  components: Record<string, unknown>;
  recent_errors_count: number;
  recent_logs_count: number;
}

interface FormulasResult {
  requested_mode: string;
  current_constants: Record<string, unknown>;
  mode_details: Record<string, unknown>;
  all_modes: string[];
}

interface ErrorsResult {
  total_errors: number;
  returned: number;
  errors: Array<{
    timestamp: number;
    error: string;
    source: string;
    details: Record<string, unknown>;
  }>;
}

interface LogsResult {
  total_logs: number;
  returned: number;
  logs: Array<{
    timestamp: number;
    message: string;
    category: string;
    data: Record<string, unknown>;
  }>;
  available_categories: string[];
}

interface DetachedMediaSnapshotResult {
  total_snapshots: number;
  returned: number;
  latest: {
    timestamp: number;
    src: string;
    path: string;
    snapshot: Record<string, unknown>;
  } | null;
  available_sources: string[];
  filter_applied: {
    path: string | null;
    src: string | null;
  };
}

interface ModesResult {
  modes: Record<string, {
    name: string;
    description: string;
    layout: string;
    cached?: boolean;
  }>;
}

interface AgentInfoResult {
  welcome: string;
  version: string;
  capabilities: Record<string, unknown>;
  endpoints: Record<string, string>;
  usage_pattern: string[];
}

interface QuickStatusResult {
  timestamp: string;
  summary: string;
  tree: TreeState;
  hasErrors: boolean;
  errorCount: number;
  components: {
    qdrant: boolean;
    memory: boolean;
  };
  redFlags: string[];
  nextSteps: string[];
}

interface CameraFocusResult {
  success: boolean;
  message?: string;
  error?: string;
  params?: {
    target: string;
    zoom: string;
    highlight: boolean;
    animate: boolean;
  };
}

interface ChatContextResult {
  timestamp: number;
  vetka_phase: string;
  project: {
    name: string;
    description: string;
    current_phase: string;
  };
  tree_summary: Record<string, unknown>;
  active_components: string[];
  recent_activity: {
    errors_count: number;
    logs_count: number;
    last_error: Record<string, unknown> | null;
  };
  chat_history: Array<Record<string, unknown>>;
  summary_for_agent: string;
}

// ============================================================
// PHASE 80.3: TEAM MESSAGING INTERFACES (monochrome design)
// ============================================================

interface AgentInfo {
  name: string;
  icon: string;  // Lucide icon name
  role: string;
  description?: string;
  capabilities?: string[];
  model_id?: string | null;  // Links to ModelRegistry MCP agent
}

interface TeamMessage {
  id: number;
  timestamp: number;
  sender: string;
  sender_info: AgentInfo;
  to: string;
  to_info: {
    name: string;
    icon: string;
    role: string;
  };
  message: string;
  priority: 'normal' | 'high' | 'urgent';
  context: Record<string, unknown>;
  read: boolean;
}

interface SendMessageResult {
  success: boolean;
  message_id: number;
  delivered_to: string;
  timestamp: number;
  tip: string;
}

interface TeamMessagesResult {
  total_messages: number;
  unread_count: number;
  returned: number;
  messages: TeamMessage[];
  filters: {
    unread_only: boolean;
    sender: string | null;
    to: string | null;
  };
}

interface TeamAgentsResult {
  agents: Record<string, AgentInfo>;
  usage: {
    tip: string;
    icons: string;
  };
}

const vetkaAPI = {
  /**
   * Quick tree health check
   */
  async getTreeState(): Promise<TreeState> {
    const response = await fetch(`${API_BASE}/tree-state`);
    const data = await response.json();
    console.log('🌳 VETKA Tree State:', data);
    return data;
  },

  /**
   * Full state inspection
   * @param keyword Optional filter keyword
   */
  async inspect(keyword?: string): Promise<InspectResult> {
    const url = keyword
      ? `${API_BASE}/inspect?keyword=${encodeURIComponent(keyword)}`
      : `${API_BASE}/inspect`;
    const response = await fetch(url);
    const data = await response.json();
    console.log('🔍 VETKA Inspect:', data);
    return data;
  },

  /**
   * Get layout formula values
   * @param mode Layout mode (directory, knowledge, force_directed)
   */
  async getFormulas(mode: string = 'directory'): Promise<FormulasResult> {
    const response = await fetch(`${API_BASE}/formulas?mode=${encodeURIComponent(mode)}`);
    const data = await response.json();
    console.log(`📐 VETKA Formulas (${mode}):`, data);
    return data;
  },

  /**
   * Get recent errors
   * @param limit Number of errors to return
   * @param source Optional source filter
   */
  async getErrors(limit: number = 20, source?: string): Promise<ErrorsResult> {
    let url = `${API_BASE}/recent-errors?limit=${limit}`;
    if (source) url += `&source_filter=${encodeURIComponent(source)}`;
    const response = await fetch(url);
    const data = await response.json();
    console.log('❌ VETKA Errors:', data);
    return data;
  },

  /**
   * Get debug logs
   * @param limit Number of logs to return
   * @param category Optional category filter
   */
  async getLogs(limit: number = 50, category?: string): Promise<LogsResult> {
    let url = `${API_BASE}/logs?limit=${limit}`;
    if (category) url += `&category=${encodeURIComponent(category)}`;
    const response = await fetch(url);
    const data = await response.json();
    console.log('📋 VETKA Logs:', data);
    return data;
  },

  /**
   * Get latest detached media window geometry snapshot captured by renderer debug tooling.
   */
  async getDetachedMediaSnapshot(path?: string, src?: string): Promise<DetachedMediaSnapshotResult> {
    const params = new URLSearchParams();
    if (path) params.set('path', path);
    if (src) params.set('src', src);
    const suffix = params.toString() ? `?${params.toString()}` : '';
    const response = await fetch(`${API_BASE}/media-window-snapshot${suffix}`);
    const data = await response.json();
    console.log('🎬 VETKA Detached Media Snapshot:', data);
    return data;
  },

  /**
   * Get visualization modes info
   */
  async getModes(): Promise<ModesResult> {
    const response = await fetch(`${API_BASE}/modes`);
    const data = await response.json();
    console.log('🎨 VETKA Modes:', data);
    return data;
  },

  /**
   * Get agent help info
   */
  async getAgentInfo(): Promise<AgentInfoResult> {
    const response = await fetch(`${API_BASE}/agent-info`);
    const data = await response.json();
    console.log('ℹ️ VETKA Agent Info:', data);
    return data;
  },

  /**
   * Control 3D camera - focus on file, branch, or overview
   * @param target File path (e.g., 'src/main.py'), branch name, or 'overview'
   * @param zoom Zoom level: 'close', 'medium', or 'far'
   * @param highlight Whether to highlight the target with glow
   * @param animate Whether to animate the camera movement
   */
  async focusCamera(
    target: string,
    zoom: 'close' | 'medium' | 'far' = 'medium',
    highlight: boolean = true,
    animate: boolean = true
  ): Promise<CameraFocusResult> {
    const response = await fetch(`${API_BASE}/camera-focus`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, zoom, highlight, animate })
    });
    const data = await response.json();

    if (data.success) {
      console.log(`🎥 Camera focusing on '${target}' (zoom=${zoom})`);
    } else {
      console.log('❌ Camera focus failed:', data.error);
    }

    return data;
  },

  /**
   * Get chat context - the same data internal agents receive
   * @param includeHistory Whether to include recent chat messages
   * @param historyLimit How many messages to include
   */
  async getChatContext(includeHistory: boolean = false, historyLimit: number = 10): Promise<ChatContextResult> {
    const url = `${API_BASE}/chat-context?include_history=${includeHistory}&history_limit=${historyLimit}`;
    const response = await fetch(url);
    const data = await response.json();

    console.log('💬 VETKA Chat Context:');
    console.log(`   Phase: ${data.vetka_phase}`);
    console.log(`   Files: ${data.tree_summary?.total_files || '?'}`);
    console.log(`   Components: ${data.active_components?.join(', ') || 'unknown'}`);
    console.log(`   Summary: ${data.summary_for_agent}`);

    return data;
  },

  /**
   * ONE COMMAND status check - perfect for new sessions!
   * Returns everything an agent needs to know in one call.
   */
  async quickStatus(): Promise<QuickStatusResult> {
    console.log('🔍 VETKA Quick Status Check...\n');

    // Fetch all data in parallel
    const [treeResponse, errorsResponse, inspectResponse] = await Promise.all([
      fetch(`${API_BASE}/tree-state`),
      fetch(`${API_BASE}/recent-errors?limit=10`),
      fetch(`${API_BASE}/inspect`)
    ]);

    const tree: TreeState = await treeResponse.json();
    const errors: ErrorsResult = await errorsResponse.json();
    const inspect: InspectResult = await inspectResponse.json();

    // Analyze red flags
    const redFlags: string[] = [];
    if (!tree.healthy) redFlags.push('Tree unhealthy!');
    if (tree.status === 'red') redFlags.push('Status RED!');
    if (!inspect.qdrant_connected) redFlags.push('Qdrant disconnected!');
    if (!inspect.memory_manager_active) redFlags.push('Memory manager inactive!');
    if (errors.total_errors > 0) redFlags.push(`${errors.total_errors} errors found!`);

    // Suggest next steps
    const nextSteps: string[] = [];
    if (redFlags.length === 0) {
      nextSteps.push('All good! Ready to help with debugging.');
    } else {
      if (!tree.healthy) nextSteps.push('Run getTreeState() for details');
      if (errors.total_errors > 0) nextSteps.push('Run getErrors() to see error details');
      if (!inspect.qdrant_connected) nextSteps.push('Check if Qdrant is running on port 6333');
      nextSteps.push('Report these findings to Claude Code (MCP) for fixes');
    }

    // Build summary
    const summary = redFlags.length === 0
      ? `✅ VETKA is healthy! ${tree.files_count || 0} files indexed, all systems operational.`
      : `⚠️ ${redFlags.length} issue(s) found. See redFlags array for details.`;

    const result: QuickStatusResult = {
      timestamp: new Date().toISOString(),
      summary,
      tree,
      hasErrors: errors.total_errors > 0,
      errorCount: errors.total_errors,
      components: {
        qdrant: inspect.qdrant_connected,
        memory: inspect.memory_manager_active
      },
      redFlags,
      nextSteps
    };

    // Pretty print to console
    console.log('╔══════════════════════════════════════════════════════════════╗');
    console.log('║              🌳 VETKA QUICK STATUS REPORT                    ║');
    console.log('╠══════════════════════════════════════════════════════════════╣');
    console.log(`║  ${summary.padEnd(60)}║`);
    console.log('╠══════════════════════════════════════════════════════════════╣');
    console.log(`║  Tree Health:    ${tree.healthy ? '✅ Healthy' : '❌ Unhealthy'}`.padEnd(63) + '║');
    console.log(`║  Files Indexed:  ${tree.files_count || 0}`.padEnd(63) + '║');
    console.log(`║  Qdrant:         ${inspect.qdrant_connected ? '✅ Connected' : '❌ Disconnected'}`.padEnd(63) + '║');
    console.log(`║  Memory Manager: ${inspect.memory_manager_active ? '✅ Active' : '❌ Inactive'}`.padEnd(63) + '║');
    console.log(`║  Errors:         ${errors.total_errors === 0 ? '✅ None' : `❌ ${errors.total_errors} found`}`.padEnd(63) + '║');

    if (redFlags.length > 0) {
      console.log('╠══════════════════════════════════════════════════════════════╣');
      console.log('║  🚨 RED FLAGS:                                               ║');
      redFlags.forEach(flag => {
        console.log(`║    - ${flag}`.padEnd(63) + '║');
      });
    }

    console.log('╠══════════════════════════════════════════════════════════════╣');
    console.log('║  📋 NEXT STEPS:                                              ║');
    nextSteps.forEach(step => {
      console.log(`║    → ${step}`.padEnd(63) + '║');
    });
    console.log('╚══════════════════════════════════════════════════════════════╝');

    return result;
  },

  // ============================================================
  // PHASE 80.2: TEAM MESSAGING METHODS
  // ============================================================

  /**
   * Send message to another agent (e.g., Browser Haiku → Claude Code)
   * @param message The message text
   * @param to Target agent: 'claude_code' | 'vetka_internal' | 'user' | 'all'
   * @param priority Message priority: 'normal' | 'high' | 'urgent'
   * @param context Optional context data (file paths, error details, etc.)
   */
  async sendTeamMessage(
    message: string,
    to: string = 'claude_code',
    priority: 'normal' | 'high' | 'urgent' = 'normal',
    context?: Record<string, unknown>
  ): Promise<SendMessageResult> {
    const response = await fetch(`${API_BASE}/team-message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        sender: 'browser_haiku',  // Browser agents always identify as browser_haiku
        to,
        priority,
        context: context || {}
      })
    });
    const data = await response.json();

    if (data.success) {
      console.log(`📨 Message sent to ${to} (id: ${data.message_id})`);
      console.log(`   Priority: ${priority}`);
      console.log(`   "${message.substring(0, 80)}${message.length > 80 ? '...' : ''}"`);
    } else {
      console.log('❌ Failed to send message:', data.error);
    }

    return data;
  },

  /**
   * Read team messages (check for responses from Claude Code)
   * @param limit Number of messages to return
   * @param unreadOnly Only show unread messages
   * @param markRead Mark returned messages as read
   */
  async readTeamMessages(
    limit: number = 20,
    unreadOnly: boolean = false,
    markRead: boolean = false
  ): Promise<TeamMessagesResult> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      unread_only: unreadOnly.toString(),
      to_filter: 'browser_haiku',  // Messages addressed to us
      mark_read: markRead.toString()
    });
    const response = await fetch(`${API_BASE}/team-messages?${params}`);
    const data = await response.json();

    console.log('📬 Team Messages:');
    console.log(`   Total: ${data.total_messages} | Unread: ${data.unread_count} | Showing: ${data.returned}`);

    if (data.messages.length > 0) {
      console.log('');
      data.messages.forEach((msg: TeamMessage) => {
        const time = new Date(msg.timestamp * 1000).toLocaleTimeString();
        const unread = !msg.read ? '🔵 ' : '';
        const priorityIcon = msg.priority === 'urgent' ? '🔴' : msg.priority === 'high' ? '🟠' : '';
        console.log(`   ${unread}${priorityIcon}[${time}] ${msg.sender_info.name} → ${msg.to_info.name}:`);
        console.log(`      "${msg.message.substring(0, 100)}${msg.message.length > 100 ? '...' : ''}"`);
      });
    } else {
      console.log('   No messages found.');
    }

    return data;
  },

  /**
   * Check for new messages (quick unread check)
   */
  async checkMessages(): Promise<{ unread: number; latest: TeamMessage | null }> {
    const data = await this.readTeamMessages(5, true, false);
    return {
      unread: data.unread_count,
      latest: data.messages[0] || null
    };
  },

  /**
   * Get list of known team agents
   */
  async getTeamAgents(): Promise<TeamAgentsResult> {
    const response = await fetch(`${API_BASE}/team-agents`);
    const data = await response.json();

    console.log('Team Agents:');
    Object.entries(data.agents).forEach(([key, agent]) => {
      const a = agent as AgentInfo;
      console.log(`   ${key}: ${a.name} (${a.icon})`);
      console.log(`      Role: ${a.role}`);
    });

    return data;
  },

  /**
   * Show help in console
   */
  help(): void {
    console.log(`
╔════════════════════════════════════════════════════════════════════╗
║                    VETKA Browser Agent API v1.3                    ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  🎯 START HERE (new sessions):                                     ║
║  vetkaAPI.quickStatus()         ONE command to check everything!   ║
║                                                                    ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  📊 Read state:                                                    ║
║  vetkaAPI.getTreeState()        Quick tree health check            ║
║  vetkaAPI.inspect()             Full state inspection              ║
║  vetkaAPI.inspect('blend')      Filtered inspection                ║
║  vetkaAPI.getFormulas('mode')   Layout formula values              ║
║  vetkaAPI.getErrors()           Recent errors                      ║
║  vetkaAPI.getLogs()             Debug logs                         ║
║  vetkaAPI.getDetachedMediaSnapshot() Latest media geometry         ║
║  vetkaAPI.getModes()            Visualization mode info            ║
║  vetkaAPI.getChatContext()      Chat context (like internal agents)║
║  vetkaAPI.getChatContext(true)  With chat history                  ║
║                                                                    ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  🎥 Control visualization:                                         ║
║  vetkaAPI.focusCamera('file.py')      Focus on file                ║
║  vetkaAPI.focusCamera('src/', 'far')  Focus on folder, zoomed out  ║
║  vetkaAPI.focusCamera('overview')     Show full tree               ║
║                                                                    ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  💬 TEAM MESSAGING (Phase 80.2):                                   ║
║  vetkaAPI.sendTeamMessage(msg)              Send to Claude Code    ║
║  vetkaAPI.sendTeamMessage(msg, 'all')       Broadcast to all       ║
║  vetkaAPI.sendTeamMessage(msg, to, 'urgent') Urgent priority       ║
║  vetkaAPI.readTeamMessages()                Read incoming messages ║
║  vetkaAPI.readTeamMessages(10, true)        Only unread            ║
║  vetkaAPI.checkMessages()                   Quick unread check     ║
║  vetkaAPI.getTeamAgents()                   List team members      ║
║                                                                    ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  ℹ️ Info:                                                          ║
║  vetkaAPI.getAgentInfo()        Full API documentation             ║
║  vetkaAPI.help()                Show this help                     ║
║                                                                    ║
║  📝 All methods return Promises and log results to console.        ║
║  🔒 Code changes go through Claude Code (MCP).                     ║
║  ✅ Camera, state reading, and messaging are allowed!              ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
`);
  }
};

// Expose to window
declare global {
  interface Window {
    vetkaAPI: typeof vetkaAPI;
  }
}

export function initBrowserAgentBridge(): void {
  window.vetkaAPI = vetkaAPI;
  console.log('🌳 VETKA Browser Agent Bridge initialized. Type vetkaAPI.help() for commands.');
}

export default vetkaAPI;
import { API_BASE as CORE_API_BASE } from '../config/api.config';
