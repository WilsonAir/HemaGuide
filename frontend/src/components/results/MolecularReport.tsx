import { motion } from 'framer-motion';
import { GlassCard } from '../layout/GlassCard';
import type { VariantClassification } from '../../types/agent';

interface MolecularReportProps {
  results: VariantClassification[];
  reportText?: string;
}

const CLASSIFICATION_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  'Oncogenic': { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
  'Likely Oncogenic': { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
  'VUS': { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' },
  'Likely Benign': { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  'Benign': { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
};

export function MolecularReport({ results, reportText }: MolecularReportProps) {
  if (!results || results.length === 0) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <div className="flex items-center gap-2 text-slate-600">
        <svg className="w-5 h-5 text-hemaguide-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
          />
        </svg>
        <span className="text-sm font-medium">Molecular Classification (Horak et al. 2022)</span>
      </div>

      {/* Variant Cards */}
      {results.map((variant, index) => {
        const colorConfig = CLASSIFICATION_COLORS[variant.classification] || CLASSIFICATION_COLORS['VUS'];

        return (
          <GlassCard
            key={index}
            className="p-5"
            hover={false}
          >
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <h4 className="text-lg font-semibold text-slate-900">
                  {variant.gene}
                  <span className="text-slate-500 font-normal ml-2">{variant.aa_change}</span>
                </h4>
                <p className="text-sm text-slate-500 font-mono mt-1">{variant.variant}</p>
              </div>

              <div className="flex flex-col items-end gap-2">
                <span className={`
                  px-3 py-1 rounded-lg text-sm font-medium
                  ${colorConfig.bg} ${colorConfig.text} ${colorConfig.border} border
                `}>
                  {variant.classification}
                </span>
                <span className="text-2xl font-bold text-slate-800">
                  {variant.total_points > 0 ? '+' : ''}{variant.total_points}
                  <span className="text-sm font-normal text-slate-500 ml-1">points</span>
                </span>
              </div>
            </div>

            {/* gnomAD info */}
            <div className="flex items-center gap-2 mb-4 text-sm">
              <span className="text-slate-500">gnomAD:</span>
              {variant.gnomad.found ? (
                <span className="text-amber-600">
                  AF = {variant.gnomad.af !== null ? variant.gnomad.af.toExponential(2) : 'N/A'}
                </span>
              ) : (
                <span className="text-emerald-600">Not found (rare)</span>
              )}
            </div>

            {/* Criteria met */}
            {variant.criteria_met.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs text-slate-500 uppercase tracking-wider">Criteria Met</span>
                <div className="flex flex-wrap gap-2">
                  {variant.criteria_met.map((criterion, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: idx * 0.05 }}
                      className={`
                        group relative px-3 py-1.5 rounded-lg text-sm
                        ${criterion.points > 0
                          ? 'bg-hemaguide-50 border border-hemaguide-200 text-hemaguide-700'
                          : 'bg-blue-50 border border-blue-200 text-blue-700'
                        }
                      `}
                    >
                      <span className="font-mono font-medium">{criterion.code}</span>
                      <span className="ml-2 opacity-70">
                        {criterion.points > 0 ? '+' : ''}{criterion.points}
                      </span>

                      {/* Tooltip */}
                      <div className="
                        absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2
                        bg-white border border-slate-200 rounded-lg text-xs text-slate-700
                        opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none
                        w-64 z-10 shadow-lg
                      ">
                        {criterion.description}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </GlassCard>
        );
      })}

      {/* Raw report text */}
      {reportText && (
        <GlassCard className="p-4" hover={false}>
          <details className="group">
            <summary className="text-sm text-slate-500 cursor-pointer hover:text-slate-700 transition-colors">
              Show Full Classification Report
            </summary>
            <pre className="mt-4 text-xs text-slate-600 font-mono whitespace-pre-wrap overflow-x-auto scrollbar-thin">
              {reportText}
            </pre>
          </details>
        </GlassCard>
      )}
    </motion.div>
  );
}
