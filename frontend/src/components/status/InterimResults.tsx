import { motion, AnimatePresence } from 'framer-motion';
import { GlassCard } from '../layout/GlassCard';
import type { CaseResult } from '../../types/agent';

interface InterimResultsProps {
  caseResults: CaseResult[];
  isProcessing: boolean;
}

const MODE_CONFIG = {
  GUIDELINE: {
    label: 'GUIDELINE',
    color: 'text-purple-700',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
  },
  ADVANCED: {
    label: 'ADVANCED',
    color: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
  },
  MOLECULAR: {
    label: 'MOLECULAR',
    color: 'text-hemaguide-700',
    bgColor: 'bg-hemaguide-50',
    borderColor: 'border-hemaguide-200',
  },
};

export function InterimResults({ caseResults, isProcessing }: InterimResultsProps) {
  if (caseResults.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent" />
        <span className="text-sm text-emerald-400 px-4 flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          {caseResults.length} case{caseResults.length !== 1 ? 's' : ''} completed
        </span>
        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent" />
      </div>

      <AnimatePresence mode="popLayout">
        {caseResults.map((caseResult, index) => {
          const modeConfig = MODE_CONFIG[caseResult.mode] || MODE_CONFIG.GUIDELINE;

          return (
            <motion.div
              key={caseResult.case_id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ delay: index * 0.1 }}
            >
              <GlassCard
                className={`p-5 ${modeConfig.bgColor} ${modeConfig.borderColor}`}
                hover={false}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`
                      w-10 h-10 rounded-xl flex items-center justify-center
                      ${modeConfig.bgColor} border ${modeConfig.borderColor}
                    `}>
                      <motion.svg
                        initial={{ scale: 0, rotate: -180 }}
                        animate={{ scale: 1, rotate: 0 }}
                        className={`w-5 h-5 ${modeConfig.color}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </motion.svg>
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-800">{caseResult.case_name}</h4>
                      <span className={`text-xs ${modeConfig.color}`}>{modeConfig.label} Mode</span>
                    </div>
                  </div>
                  <span className="text-xs text-slate-400">
                    {new Date(caseResult.completed_at).toLocaleTimeString('en-US')}
                  </span>
                </div>

                {/* Decision */}
                <div className="mb-4">
                  <h5 className="text-xs text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    Decision
                  </h5>
                  <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                    {caseResult.konferenzbeschluss || 'No decision available'}
                  </p>
                </div>

                {/* Reasoning - Collapsible */}
                <details className="group">
                  <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-700 transition-colors flex items-center gap-2">
                    <svg className="w-3.5 h-3.5 group-open:rotate-90 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    Show Reasoning
                  </summary>
                  <div className="mt-3 pt-3 border-t border-slate-200">
                    <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                      {caseResult.begründung || 'No reasoning available'}
                    </p>
                  </div>
                </details>
              </GlassCard>
            </motion.div>
          );
        })}
      </AnimatePresence>

      {/* Processing indicator */}
      {isProcessing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center gap-2 text-sm text-slate-500 py-2"
        >
          <motion.div
            className="w-4 h-4 border-2 border-hemaguide-200 border-t-hemaguide-500 rounded-full"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          />
          Processing additional cases...
        </motion.div>
      )}
    </div>
  );
}
