import { motion, AnimatePresence } from 'framer-motion';
import { GlassCard } from '../layout/GlassCard';
import type { ProcessingStatus } from '../../types/agent';

interface StatusIndicatorProps {
  status: ProcessingStatus;
  message?: string;
  progress?: number;
  currentCase?: number;
  totalCases?: number;
}

const STATUS_CONFIG: Record<ProcessingStatus, {
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
}> = {
  idle: {
    label: 'Ready',
    color: 'text-slate-500',
    bgColor: 'bg-slate-50',
    borderColor: 'border-slate-200'
  },
  queued: {
    label: 'Queued',
    color: 'text-slate-600',
    bgColor: 'bg-slate-50',
    borderColor: 'border-slate-200'
  },
  uploading: {
    label: 'Uploading',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200'
  },
  extracting: {
    label: 'Extraction',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200'
  },
  routing: {
    label: 'Agent Routing',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200'
  },
  generating: {
    label: 'Generating',
    color: 'text-hemaguide-600',
    bgColor: 'bg-hemaguide-50',
    borderColor: 'border-hemaguide-200'
  },
  complete: {
    label: 'Complete',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200'
  },
  error: {
    label: 'Error',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200'
  },
};

export function StatusIndicator({ status, message, progress, currentCase, totalCases }: StatusIndicatorProps) {
  const config = STATUS_CONFIG[status];
  const isActive = !['idle', 'complete', 'error'].includes(status);
  const hasCaseProgress = currentCase !== undefined && totalCases !== undefined && totalCases > 0;

  return (
    <GlassCard
      className={`p-4 ${config.bgColor} ${config.borderColor}`}
      hover={false}
    >
      <div className="flex items-center gap-4">
        {/* Status Icon */}
        <div className="relative">
          <motion.div
            className={`w-10 h-10 rounded-xl ${config.bgColor} border ${config.borderColor} flex items-center justify-center`}
            animate={isActive ? {
              boxShadow: [
                '0 0 0 0 rgba(6, 182, 212, 0)',
                '0 0 0 8px rgba(6, 182, 212, 0.1)',
                '0 0 0 0 rgba(6, 182, 212, 0)'
              ]
            } : {}}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            {status === 'complete' ? (
              <motion.svg
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                className={`w-5 h-5 ${config.color}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </motion.svg>
            ) : status === 'error' ? (
              <svg className={`w-5 h-5 ${config.color}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : isActive ? (
              <motion.svg
                animate={{ rotate: 360 }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                className={`w-5 h-5 ${config.color}`}
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </motion.svg>
            ) : (
              <div className={`w-3 h-3 rounded-full ${status === 'idle' ? 'bg-slate-300' : config.bgColor}`} />
            )}
          </motion.div>
        </div>

        {/* Status Text */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`font-medium ${config.color}`}>{config.label}</span>
            {hasCaseProgress && (
              <span className="text-sm text-slate-500">
                Case {currentCase} of {totalCases}
              </span>
            )}
          </div>
          <AnimatePresence mode="wait">
            {message && (
              <motion.div
                key={message}
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 5 }}
                className="text-sm text-slate-500 mt-0.5 truncate"
              >
                {message}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Progress Section */}
        {isActive && (
          <div className="w-32 flex-shrink-0">
            {/* Case counter badge */}
            {hasCaseProgress && (
              <div className="flex justify-center mb-2">
                <span className={`
                  px-3 py-1 rounded-lg text-sm font-bold
                  ${config.bgColor} ${config.color} border ${config.borderColor}
                `}>
                  {currentCase}/{totalCases}
                </span>
              </div>
            )}
            {/* Progress bar */}
            {progress !== undefined && (
              <div>
                <div className="flex justify-between text-xs text-slate-500 mb-1">
                  <span>Progress</span>
                  <span>{progress}%</span>
                </div>
                <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-hemaguide-600 to-hemaguide-500 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.5, ease: 'easeOut' }}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </GlassCard>
  );
}
