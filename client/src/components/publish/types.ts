/**
 * MARKER_GAMMA-P2: Cross-Platform Publish Types
 * From RECON_CROSS_PLATFORM_PUBLISH_ARCHITECTURE_2026-03-25
 */

export type Platform =
  | 'youtube'
  | 'instagram'
  | 'tiktok'
  | 'x'
  | 'telegram'
  | 'file';

export type ReframeMode = 'center' | 'ai-track' | 'manual';

export type PublishJobStatus =
  | 'pending'
  | 'encoding'
  | 'uploading'
  | 'scheduled'
  | 'done'
  | 'error';

export interface PlatformConstraints {
  platform: Platform;
  codec: string[];
  aspectRatios: string[];
  maxDurationSeconds: number;
  maxFileSizeBytes: number;
  maxResolutionW: number;
  maxResolutionH: number;
  requiresAspectRatio?: string;
}

export interface PlatformMetadata {
  title: string;
  description: string;
  tags: string[];
  coverImageTimecode?: string;
  hashtags?: string[];
  location?: string;
  isShorts?: boolean;
  isDocument?: boolean;
  scheduleAt?: Date | null;
}

export interface PlatformTarget {
  platform: Platform;
  enabled: boolean;
  constraints: PlatformConstraints;
  metadata: PlatformMetadata;
  reframeMode: ReframeMode;
}

export interface PublishJob {
  id: string;
  platform: Platform;
  status: PublishJobStatus;
  encodeProgress: number;
  uploadProgress: number;
  outputUrl?: string;
  errorMessage?: string;
  startedAt: number;
  completedAt?: number;
}

/** Platform constraints registry — from architecture doc table */
export const PLATFORM_CONSTRAINTS: Record<Platform, PlatformConstraints> = {
  youtube: {
    platform: 'youtube',
    codec: ['H.264', 'VP9', 'AV1'],
    aspectRatios: ['16:9', '9:16', '1:1'],
    maxDurationSeconds: 43200,
    maxFileSizeBytes: Infinity,
    maxResolutionW: 7680,
    maxResolutionH: 4320,
  },
  instagram: {
    platform: 'instagram',
    codec: ['H.264'],
    aspectRatios: ['9:16'],
    maxDurationSeconds: 90,
    maxFileSizeBytes: 4 * 1024 * 1024 * 1024,
    maxResolutionW: 1080,
    maxResolutionH: 1920,
    requiresAspectRatio: '9:16',
  },
  tiktok: {
    platform: 'tiktok',
    codec: ['H.264'],
    aspectRatios: ['9:16'],
    maxDurationSeconds: 600,
    maxFileSizeBytes: 4 * 1024 * 1024 * 1024,
    maxResolutionW: 1080,
    maxResolutionH: 1920,
    requiresAspectRatio: '9:16',
  },
  x: {
    platform: 'x',
    codec: ['H.264'],
    aspectRatios: ['16:9', '1:1', '9:16'],
    maxDurationSeconds: 140,
    maxFileSizeBytes: 512 * 1024 * 1024,
    maxResolutionW: 1920,
    maxResolutionH: 1080,
  },
  telegram: {
    platform: 'telegram',
    codec: ['H.264'],
    aspectRatios: ['any'],
    maxDurationSeconds: Infinity,
    maxFileSizeBytes: 2 * 1024 * 1024 * 1024,
    maxResolutionW: Infinity,
    maxResolutionH: Infinity,
  },
  file: {
    platform: 'file',
    codec: ['ProRes', 'DNxHR', 'H.264', 'H.265', 'VP9', 'AV1'],
    aspectRatios: ['any'],
    maxDurationSeconds: Infinity,
    maxFileSizeBytes: Infinity,
    maxResolutionW: Infinity,
    maxResolutionH: Infinity,
  },
};

export const PLATFORM_LABELS: Record<Platform, string> = {
  youtube: 'YouTube',
  instagram: 'Instagram',
  tiktok: 'TikTok',
  x: 'X / Twitter',
  telegram: 'Telegram',
  file: 'File Export',
};

/** Default metadata factory */
export function createDefaultMetadata(projectTitle = ''): PlatformMetadata {
  return {
    title: projectTitle,
    description: '',
    tags: [],
    scheduleAt: null,
  };
}

/** Default target factory */
export function createDefaultTarget(platform: Platform, projectTitle = ''): PlatformTarget {
  return {
    platform,
    enabled: false,
    constraints: PLATFORM_CONSTRAINTS[platform],
    metadata: createDefaultMetadata(projectTitle),
    reframeMode: 'center',
  };
}
