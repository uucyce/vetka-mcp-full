/**
 * MARKER_GEN-CONFIG: Generation provider metadata + param schemas.
 * Single source of truth for provider capabilities used by store + UI.
 *
 * @phase GENERATION_CONTROL
 * @task tb_1774432024_1
 */

export type ProviderCategory = 'video' | 'music' | 'voice' | 'upscale';
export type ProviderConnectionType = 'api' | 'local';

export interface ParamSchema {
  key: string;
  label: string;
  type: 'select' | 'number' | 'text';
  options?: string[];
  min?: number;
  max?: number;
  step?: number;
  default: string | number;
  unit?: string;
}

export interface ProviderDef {
  id: string;
  name: string;
  monogram: string;
  type: ProviderConnectionType;
  category: ProviderCategory;
  /** Cost per generation unit (USD) — used for live estimate */
  costPerUnit: number;
  /** What "one unit" means for this provider */
  costUnit: string;
  paramSchema: ParamSchema[];
}

export const GENERATION_PROVIDERS: ProviderDef[] = [
  {
    id: 'runway',
    name: 'Runway Gen-3',
    monogram: 'R',
    type: 'api',
    category: 'video',
    costPerUnit: 0.05,
    costUnit: 'per second',
    paramSchema: [
      { key: 'duration', label: 'Duration (s)', type: 'number', min: 5, max: 30, step: 5, default: 5 },
      { key: 'ratio', label: 'Aspect Ratio', type: 'select', options: ['16:9', '9:16', '1:1'], default: '16:9' },
      { key: 'motion', label: 'Motion Intensity', type: 'number', min: 1, max: 10, step: 1, default: 5 },
    ],
  },
  {
    id: 'sora',
    name: 'OpenAI Sora',
    monogram: 'S',
    type: 'api',
    category: 'video',
    costPerUnit: 0.12,
    costUnit: 'per second',
    paramSchema: [
      { key: 'duration', label: 'Duration (s)', type: 'number', min: 5, max: 60, step: 5, default: 5 },
      { key: 'resolution', label: 'Resolution', type: 'select', options: ['1080p', '720p', '480p'], default: '1080p' },
    ],
  },
  {
    id: 'kling',
    name: 'Kling',
    monogram: 'K',
    type: 'api',
    category: 'video',
    costPerUnit: 0.03,
    costUnit: 'per second',
    paramSchema: [
      { key: 'duration', label: 'Duration (s)', type: 'number', min: 5, max: 10, step: 5, default: 5 },
      { key: 'mode', label: 'Mode', type: 'select', options: ['standard', 'professional'], default: 'standard' },
    ],
  },
  {
    id: 'flux',
    name: 'FLUX.1',
    monogram: 'F',
    type: 'local',
    category: 'video',
    costPerUnit: 0,
    costUnit: 'local',
    paramSchema: [
      { key: 'steps', label: 'Steps', type: 'number', min: 10, max: 50, step: 5, default: 20 },
      { key: 'guidance', label: 'Guidance', type: 'number', min: 1, max: 20, step: 0.5, default: 7.5 },
    ],
  },
  {
    id: 'sdxl',
    name: 'SDXL',
    monogram: 'X',
    type: 'local',
    category: 'video',
    costPerUnit: 0,
    costUnit: 'local',
    paramSchema: [
      { key: 'steps', label: 'Steps', type: 'number', min: 10, max: 50, step: 5, default: 30 },
      { key: 'guidance', label: 'Guidance', type: 'number', min: 1, max: 20, step: 0.5, default: 7 },
      { key: 'width', label: 'Width', type: 'select', options: ['512', '768', '1024'], default: '1024' },
    ],
  },
  {
    id: 'suno',
    name: 'Suno',
    monogram: 'U',
    type: 'api',
    category: 'music',
    costPerUnit: 0.01,
    costUnit: 'per track',
    paramSchema: [
      { key: 'duration', label: 'Duration (s)', type: 'number', min: 15, max: 120, step: 15, default: 30 },
      { key: 'style', label: 'Style', type: 'text', default: 'cinematic' },
    ],
  },
  {
    id: 'udio',
    name: 'Udio',
    monogram: 'D',
    type: 'api',
    category: 'music',
    costPerUnit: 0.01,
    costUnit: 'per track',
    paramSchema: [
      { key: 'duration', label: 'Duration (s)', type: 'number', min: 15, max: 120, step: 15, default: 30 },
    ],
  },
  {
    id: 'elevenlabs',
    name: 'ElevenLabs',
    monogram: 'E',
    type: 'api',
    category: 'voice',
    costPerUnit: 0.0003,
    costUnit: 'per char',
    paramSchema: [
      { key: 'voice', label: 'Voice', type: 'select', options: ['Rachel', 'Adam', 'Bella', 'Josh'], default: 'Rachel' },
      { key: 'stability', label: 'Stability', type: 'number', min: 0, max: 1, step: 0.1, default: 0.5 },
      { key: 'similarity', label: 'Similarity', type: 'number', min: 0, max: 1, step: 0.1, default: 0.75 },
    ],
  },
  {
    id: 'realesrgan',
    name: 'Real-ESRGAN',
    monogram: 'G',
    type: 'local',
    category: 'upscale',
    costPerUnit: 0,
    costUnit: 'local',
    paramSchema: [
      { key: 'scale', label: 'Scale', type: 'select', options: ['2x', '4x'], default: '4x' },
      { key: 'model', label: 'Model', type: 'select', options: ['realesrgan-x4plus', 'realesrgan-x4plus-anime'], default: 'realesrgan-x4plus' },
    ],
  },
  {
    id: 'topaz',
    name: 'Topaz Video AI',
    monogram: 'T',
    type: 'local',
    category: 'upscale',
    costPerUnit: 0,
    costUnit: 'local',
    paramSchema: [
      { key: 'model', label: 'Model', type: 'select', options: ['Proteus', 'Iris', 'Gaia'], default: 'Proteus' },
      { key: 'scale', label: 'Scale', type: 'select', options: ['2x', '4x'], default: '2x' },
    ],
  },
];

export const PROVIDER_MAP = new Map<string, ProviderDef>(
  GENERATION_PROVIDERS.map((p) => [p.id, p]),
);
