import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassCard } from '../layout/GlassCard';

interface LogViewerProps {
  logs: string[];
  isExpanded?: boolean;
}

export function LogViewer({ logs, isExpanded: initialExpanded = false }: LogViewerProps) {
  const [isExpanded, setIsExpanded] = useState(initialExpanded);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (scrollRef.current && isExpanded) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, isExpanded]);

  if (logs.length === 0) return null;

  return (
    <GlassCard className="overflow-hidden" hover={false}>
      {/* Header - always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center">
            <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
          <div>
            <span className="text-sm font-medium text-slate-700">Console Output</span>
            <span className="ml-2 text-xs text-slate-400">({logs.length} lines)</span>
          </div>
        </div>
        <motion.svg
          animate={{ rotate: isExpanded ? 180 : 0 }}
          className="w-5 h-5 text-slate-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </motion.svg>
      </button>

      {/* Expandable log content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div
              ref={scrollRef}
              className="max-h-64 overflow-y-auto border-t border-slate-200 bg-slate-50"
            >
              <div className="p-3 font-mono text-xs space-y-0.5">
                {logs.map((log, index) => (
                  <LogLine key={index} log={log} index={index} />
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
}

function LogLine({ log, index }: { log: string; index: number }) {
  // Parse log type from content
  const isError = log.toLowerCase().includes('error') || log.toLowerCase().includes('failed');
  const isWarning = log.toLowerCase().includes('warning') || log.toLowerCase().includes('warn');
  const isSuccess = log.toLowerCase().includes('done') || log.toLowerCase().includes('complete') || log.toLowerCase().includes('saved');
  const isProgress = log.includes('[') && log.includes('/') && log.includes(']');

  let textColor = 'text-slate-600';
  if (isError) textColor = 'text-red-600';
  else if (isWarning) textColor = 'text-amber-600';
  else if (isSuccess) textColor = 'text-emerald-600';
  else if (isProgress) textColor = 'text-hemaguide-600';

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index * 0.02, 0.5) }}
      className={`${textColor} leading-relaxed break-all`}
    >
      {log}
    </motion.div>
  );
}
