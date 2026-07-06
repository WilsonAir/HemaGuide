import { GlassCard } from '../layout/GlassCard';
import type { Config, LLMMode } from '../../types/agent';

interface ConfigPanelProps {
  config: Config;
  onConfigChange: (config: Config) => void;
  disabled: boolean;
}

const BACKENDS: Array<{ value: LLMMode; label: string; hint: string }> = [
  {
    value: 'openai',
    label: 'OpenAI API (DashScope)',
    hint: 'OpenAI-compatible API via OPENAI_BASE_URL (e.g. DashScope qwen-plus)',
  },
  {
    value: 'ollama-local',
    label: 'Ollama (CPU)',
    hint: 'Local Ollama server (localhost:11434)',
  },
  {
    value: 'vllm',
    label: 'vLLM (GPU)',
    hint: 'Local vLLM server (localhost:8010/v1)',
  },
];

const OPENAI_MODELS = [
  { value: 'qwen-plus', label: 'Qwen Plus (Recommended)' },
  { value: 'qwen-flash', label: 'Qwen Flash (Fast)' },
  { value: 'qwen-max', label: 'Qwen Max' },
];

const OLLAMA_MODELS = [
  { value: 'gpt-oss:120b', label: 'GPT-OSS 120B (Recommended)' },
  { value: 'qwen3-next:80b', label: 'Qwen3-Next 80B' },
];

const VLLM_MODELS = [
  { value: 'gpt-oss-20b', label: 'GPT-OSS 20B (Recommended)' },
];

const DEFAULT_MODEL: Record<LLMMode, string> = {
  openai: 'qwen-plus',
  'ollama-local': 'gpt-oss:120b',
  vllm: 'gpt-oss-20b',
};

export function ConfigPanel({ config, onConfigChange, disabled }: ConfigPanelProps) {
  const models =
    config.llmMode === 'openai'
      ? OPENAI_MODELS
      : config.llmMode === 'vllm'
        ? VLLM_MODELS
        : OLLAMA_MODELS;
  const backendHint = BACKENDS.find(b => b.value === config.llmMode)?.hint ?? '';

  const handleBackendChange = (llmMode: LLMMode) => {
    onConfigChange({ ...config, llmMode, decisionModel: DEFAULT_MODEL[llmMode] });
  };

  return (
    <GlassCard className="p-5" hover={false}>
      <h3 className="text-base font-medium text-slate-800 mb-4 flex items-center gap-2">
        <svg className="w-5 h-5 text-hemaguide-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
          />
        </svg>
        Inference Backend
      </h3>

      <div className="space-y-4">
        <div>
          <label className="block text-sm text-slate-500 mb-2">Backend</label>
          <select
            value={config.llmMode}
            onChange={e => handleBackendChange(e.target.value as LLMMode)}
            disabled={disabled}
            className={`glass-select ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {BACKENDS.map(backend => (
              <option key={backend.value} value={backend.value} className="bg-white text-slate-900">
                {backend.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-slate-500 mb-2">Model</label>
          <select
            value={config.decisionModel}
            onChange={e => onConfigChange({ ...config, decisionModel: e.target.value })}
            disabled={disabled}
            className={`glass-select ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {models.map(model => (
              <option key={model.value} value={model.value} className="bg-white text-slate-900">
                {model.label}
              </option>
            ))}
          </select>
        </div>

        <p className="text-xs text-slate-400 pt-2">
          {backendHint}
        </p>
      </div>
    </GlassCard>
  );
}
