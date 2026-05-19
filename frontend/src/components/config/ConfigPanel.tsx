import { GlassCard } from '../layout/GlassCard';
import type { Config } from '../../types/agent';

interface ConfigPanelProps {
  config: Config;
  onConfigChange: (config: Config) => void;
  disabled: boolean;
}

const MODELS = [
  { value: 'gpt-oss:120b', label: 'GPT-OSS 120B (Recommended)' },
  { value: 'qwen3-next:80b', label: 'Qwen3-Next 80B' },
];

export function ConfigPanel({ config, onConfigChange, disabled }: ConfigPanelProps) {
  return (
    <GlassCard className="p-5" hover={false}>
      <h3 className="text-base font-medium text-slate-800 mb-4 flex items-center gap-2">
        <svg className="w-5 h-5 text-hemaguide-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
          />
        </svg>
        Local Models
      </h3>

      <div className="space-y-4">
        {/* Model Selection */}
        <div>
          <label className="block text-sm text-slate-500 mb-2">Model</label>
          <select
            value={config.decisionModel}
            onChange={e => onConfigChange({ ...config, decisionModel: e.target.value })}
            disabled={disabled}
            className={`glass-select ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {MODELS.map(model => (
              <option key={model.value} value={model.value} className="bg-white text-slate-900">
                {model.label}
              </option>
            ))}
          </select>
        </div>

        {/* Info text */}
        <p className="text-xs text-slate-400 pt-2">
          Local Ollama Server (localhost:11434)
        </p>
      </div>
    </GlassCard>
  );
}
