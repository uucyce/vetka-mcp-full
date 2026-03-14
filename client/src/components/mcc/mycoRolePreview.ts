import type { MiniContextPayload } from './MiniContext';
import mycoIdleQuestion from '../../assets/myco/myco_idle_question.png';
import mycoReadySmile from '../../assets/myco/myco_ready_smile.png';
import mycoSpeakingLoop from '../../assets/myco/myco_speaking_loop.apng';
import architectPrimaryStatic from '../../assets/myco/team_A/architect_primary.png';
import coderCoder1Static from '../../assets/myco/team_A/coder_coder1.png';
import coderCoder2Static from '../../assets/myco/team_A/coder_coder2.png';
import researcherPrimaryStatic from '../../assets/myco/team_A/researcher_primary.png';
import scoutScout1Static from '../../assets/myco/team_A/scout_scout1.png';
import scoutScout2Static from '../../assets/myco/team_A/scout_scout2.png';
import scoutScout3Static from '../../assets/myco/team_A/scout_scout3.png';
import verifierPrimaryStatic from '../../assets/myco/team_A/verifier_primary.png';
// MARKER_175.APNG_OPT: Animated WebP (200px, lossy q75) — 110MB→3.9MB (28x)
import architectPrimaryMotion from '../../assets/myco/architect_primary.webp';
import coderCoder1Motion from '../../assets/myco/coder_coder1.webp';
import coderCoder2Motion from '../../assets/myco/coder_coder2.webp';
import researcherPrimaryMotion from '../../assets/myco/researcher_primary.webp';
import scoutScout1Motion from '../../assets/myco/scout_scout1.webp';
import scoutScout2Motion from '../../assets/myco/scout_scout2.webp';
import scoutScout3Motion from '../../assets/myco/scout_scout3.webp';
import verifierPrimaryMotion from '../../assets/myco/verifier_primary.webp';

export type MycoRolePreviewRole = 'architect' | 'coder' | 'researcher' | 'scout' | 'verifier';
export type MycoVisualState = 'idle' | 'ready' | 'speaking';

const SYSTEM_MYCO_ASSETS: Record<MycoVisualState, string> = {
  idle: mycoIdleQuestion,
  ready: mycoReadySmile,
  speaking: mycoSpeakingLoop,
};

// MARKER_168.MYCO.RUNTIME.TEAM_A_STATIC_ROLE_ICONS.V1:
// Team_A is the canonical static icon pack for role-aware MCC surfaces.
const ROLE_STATIC_ASSETS: Record<MycoRolePreviewRole, string[]> = {
  architect: [architectPrimaryStatic],
  coder: [coderCoder1Static, coderCoder2Static],
  researcher: [researcherPrimaryStatic],
  scout: [scoutScout1Static, scoutScout2Static, scoutScout3Static],
  verifier: [verifierPrimaryStatic],
};

// MARKER_168.MYCO.RUNTIME.TEAM_A_MOTION_ROLE_ICONS.V1:
// APNG motion pack is reserved for transition pulses, not steady-state UI chrome.
const ROLE_MOTION_ASSETS: Record<MycoRolePreviewRole, string[]> = {
  architect: [architectPrimaryMotion],
  coder: [coderCoder1Motion, coderCoder2Motion],
  researcher: [researcherPrimaryMotion],
  scout: [scoutScout1Motion, scoutScout2Motion, scoutScout3Motion],
  verifier: [verifierPrimaryMotion],
};

function stableHash(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = ((hash << 5) - hash + value.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

function normalizeRole(role?: string): MycoRolePreviewRole | null {
  const value = String(role || '').trim().toLowerCase();
  if (value === 'eval') return 'verifier';
  if (value === 'architect' || value === 'coder' || value === 'researcher' || value === 'scout' || value === 'verifier') {
    return value;
  }
  return null;
}

export function resolveRolePreviewRole(context?: MiniContextPayload): MycoRolePreviewRole | null {
  const directRole = normalizeRole(context?.role);
  if (directRole) return directRole;
  if (context?.nodeKind === 'task' || context?.taskId) return 'architect';
  if (context?.workflowId || context?.workflowFamily || String(context?.graphKind || '').startsWith('workflow_')) return 'architect';
  return null;
}

export function resolveRolePreviewAsset(role: MycoRolePreviewRole | null, seed: string): string | null {
  if (!role) return null;
  const variants = ROLE_STATIC_ASSETS[role] || [];
  if (!variants.length) return null;
  const index = stableHash(`${role}:${seed}`) % variants.length;
  return variants[index] || variants[0] || null;
}

export function resolveRoleMotionAsset(role: MycoRolePreviewRole | null, seed: string): string | null {
  if (!role) return null;
  const variants = ROLE_MOTION_ASSETS[role] || [];
  if (!variants.length) return null;
  const index = stableHash(`motion:${role}:${seed}`) % variants.length;
  return variants[index] || variants[0] || null;
}

export function resolveWorkflowLeadRole(input: {
  id?: string;
  title?: string;
  description?: string;
  compatibility_tags?: string[];
}): MycoRolePreviewRole {
  const title = String(input?.title || '').toLowerCase();
  const description = String(input?.description || '').toLowerCase();
  const id = String(input?.id || '').toLowerCase();
  const tags = Array.isArray(input?.compatibility_tags)
    ? input.compatibility_tags.map((v) => String(v).toLowerCase())
    : [];
  const hay = [title, description, id, tags.join(' ')].join(' ');

  // MARKER_168.MYCO.RUNTIME.WORKFLOW_LEAD_ROLE_RESOLUTION.V1:
  // Use the first role implied by workflow semantics so compact Stats can reflect
  // live workflow choice without inventing a second chooser surface.
  if (title.includes('researcher') || hay.includes('research_first') || tags.includes('learn')) return 'researcher';
  if (title.includes('scout') || hay.includes('docs_update') || hay.includes('quick_fix') || hay.includes('test_only')) return 'scout';
  if (title.includes('coder') || hay.includes('ralph_loop') || hay.includes('critic_coder')) return 'coder';
  if (title.includes('verifier') || hay.includes('verify')) return 'verifier';
  return 'architect';
}

export function resolveMiniChatCompactAvatar(context: MiniContextPayload | undefined, visualState: MycoVisualState): string {
  const role = resolveRolePreviewRole(context);
  if (!role || visualState === 'idle') return SYSTEM_MYCO_ASSETS[visualState];
  const seed = [String(context?.taskId || ''), String(context?.nodeId || ''), String(context?.label || ''), String(context?.role || '')].join('::');
  return resolveRolePreviewAsset(role, seed) || SYSTEM_MYCO_ASSETS[visualState];
}

export function resolveMiniStatsCompactRoleAsset(context: MiniContextPayload | undefined): string | null {
  const role = resolveRolePreviewRole(context);
  if (!role) return null;
  const seed = [String(context?.taskId || ''), String(context?.nodeId || ''), String(context?.label || ''), String(context?.role || '')].join('::');
  return resolveRolePreviewAsset(role, seed);
}

export function resolveSystemMycoAsset(state: MycoVisualState): string {
  return SYSTEM_MYCO_ASSETS[state];
}
