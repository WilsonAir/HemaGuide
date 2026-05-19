import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { checkFlowchartStatus, type FlowchartStatus, type FlowchartStatusResponse } from '../../api/client';

const STATUS_COLORS: Record<FlowchartStatus['status'], string> = {
  current: 'bg-emerald-500',
  outdated: 'bg-amber-500',
  unknown: 'bg-slate-400',
  error: 'bg-slate-400',
};

const STATUS_LABELS: Record<FlowchartStatus['status'], string> = {
  current: 'Current',
  outdated: 'Update available',
  unknown: 'Unknown',
  error: 'Error',
};

const BADGE_STYLES: Record<FlowchartStatus['status'], string> = {
  current: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  outdated: 'bg-amber-50 text-amber-700 border-amber-200',
  unknown: 'bg-slate-50 text-slate-500 border-slate-200',
  error: 'bg-slate-50 text-slate-500 border-slate-200',
};

function formatStand(stand: string | null): string {
  if (!stand) return '–';
  const [year, month] = stand.split('-');
  return `${month}/${year}`;
}

export function Header() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FlowchartStatusResponse | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  const handleCheck = async () => {
    setLoading(true);
    try {
      const data = await checkFlowchartStatus();
      setResult(data);
      setPanelOpen(true);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const currentCount = result?.flowcharts.filter(f => f.status === 'current').length ?? 0;
  const totalCount = result?.flowcharts.length ?? 0;
  const hasOutdated = result?.flowcharts.some(f => f.status === 'outdated');

  return (
    <>
      <motion.header
        className="glass-panel px-6 py-4 mb-8"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="flex items-center gap-4">
          {/* Logo/Icon */}
          <div className="w-12 h-12 rounded-xl bg-hemaguide-500/20 border border-hemaguide-500/30 flex items-center justify-center">
            <svg className="w-7 h-7 text-hemaguide-500" viewBox="0 0 24 24" fill="none">
              {/* Outer circle ring */}
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" fill="none" />
              {/* Inner organic cell membrane */}
              <path d="M 12 5.2 C 13.5 5.2, 15 5.5, 16 6.2 C 17.1 6.9, 18.3 6.2, 18.7 7.4 C 19.1 8.6, 18 9.8, 17.2 10.8 C 16.3 12, 16.7 14, 16.3 15.5 C 15.9 17, 14.5 18.4, 12.5 18.7 C 10.5 19, 8.7 18.4, 7.3 17.2 C 5.9 16, 5.2 14, 5.2 12 C 5.2 10, 5.7 8.2, 6.9 6.9 C 8.1 5.5, 10 5.2, 12 5.2 Z" stroke="currentColor" strokeWidth="1" fill="none" />
              {/* Molecular network lines */}
              <line x1="12" y1="11.5" x2="12" y2="7.2" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
              <line x1="12" y1="11.5" x2="12" y2="16.3" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
              <line x1="12" y1="11.5" x2="15.4" y2="9.1" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
              <line x1="12" y1="11.5" x2="8.6" y2="14.4" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
              {/* Molecular nodes */}
              <circle cx="12" cy="11.5" r="1.3" fill="currentColor" />
              <circle cx="12" cy="7.2" r="1" fill="currentColor" />
              <circle cx="12" cy="16.3" r="1" fill="currentColor" />
              <circle cx="15.4" cy="9.1" r="1" fill="currentColor" />
              <circle cx="8.6" cy="14.4" r="1" fill="currentColor" />
            </svg>
          </div>

          {/* Title */}
          <div>
            <h1 className="text-xl font-semibold text-slate-900">
              Hema<span className="text-gradient-hemaguide">Guide</span>
            </h1>
            <p className="text-sm text-slate-500">
              Precision Hematology Agent
            </p>
          </div>

          {/* Currency check button */}
          <div className="ml-auto flex items-center gap-4">
            <button
              onClick={handleCheck}
              disabled={loading}
              className="glass-button px-3 py-1.5 text-sm flex items-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="w-4 h-4 animate-spin text-hemaguide-500" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="31.4 31.4" strokeLinecap="round" />
                  </svg>
                  Checking...
                </>
              ) : (
                <>
                  {result && (
                    <span className={`w-2 h-2 rounded-full ${hasOutdated ? 'bg-amber-500' : 'bg-emerald-500'}`} />
                  )}
                  Guideline check
                </>
              )}
            </button>

            {/* Status indicator */}
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              System ready
            </div>
          </div>
        </div>
      </motion.header>

      {/* Results panel */}
      <AnimatePresence>
        {panelOpen && result && (
          <motion.div
            className="glass-panel px-6 py-5 mb-8 -mt-4"
            initial={{ opacity: 0, height: 0, marginBottom: 0 }}
            animate={{ opacity: 1, height: 'auto', marginBottom: 32 }}
            exit={{ opacity: 0, height: 0, marginBottom: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          >
            {/* Header row */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <h2 className="text-sm font-semibold text-slate-700">Guideline Status</h2>
                <span className="text-xs text-slate-400">
                  {currentCount} of {totalCount} current
                </span>
              </div>
              <button
                onClick={() => setPanelOpen(false)}
                className="text-slate-400 hover:text-slate-600 transition-colors p-1"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Flowchart list */}
            <div className="space-y-2">
              {result.flowcharts.map((fc, i) => (
                <motion.div
                  key={fc.slug}
                  className="flex items-center gap-3 py-2 px-3 rounded-xl bg-slate-50/50"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_COLORS[fc.status]}`} />
                  <span className="text-sm text-slate-700 flex-1 min-w-0 truncate">{fc.name}</span>
                  <span className="text-xs flex items-center gap-2">
                    <span className="text-slate-400">Local:</span>
                    <span className="text-slate-500 tabular-nums">{formatStand(fc.local_stand)}</span>
                    <span className="text-slate-400">Online:</span>
                    <span className={`tabular-nums ${fc.status === 'outdated' ? 'text-amber-500' : 'text-slate-500'}`}>{formatStand(fc.online_stand)}</span>
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${BADGE_STYLES[fc.status]}`}>
                    {STATUS_LABELS[fc.status]}
                  </span>
                  <a
                    href={fc.onkopedia_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-slate-300 hover:text-hemaguide-500 transition-colors flex-shrink-0"
                  >
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3" />
                    </svg>
                  </a>
                </motion.div>
              ))}
            </div>

            {/* Timestamp */}
            <p className="text-xs text-slate-400 mt-3">
              Checked: {new Date(result.checked_at).toLocaleString('en-GB')}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
