export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorDark?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;

  agentName?: string;
  sandboxId?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'Sahayika',
  pageTitle: 'Sahayika — Multilingual Voice AI Health Companion',
  pageDescription:
    'Sahayika is a real-time conversational voice AI health companion powered by Gnani Prisma STT, Gnani Timbre TTS, and LiveKit.',

  supportsChatInput: true,
  supportsVideoInput: false,
  supportsScreenShare: false,
  isPreConnectBufferEnabled: true,

  logo: '/aanya-mark.svg',
  logoDark: '/aanya-mark.svg',
  accent: '#6347EE',
  accentDark: '#6347EE',
  startButtonText: 'Get started',

  audioVisualizerType: 'aura',
  audioVisualizerColor: '#6347EE',
  audioVisualizerColorDark: '#6347EE',
  audioVisualizerColorShift: 0.45,

  agentName: process.env.AGENT_NAME ?? 'Sahayika',
  sandboxId: undefined,
};
