import { motion } from 'framer-motion';
import { GlassCard } from '../layout/GlassCard';

interface AdvancedContextProps {
  caseSynthesis?: string;
  pubmedSynthesis?: string;
  similarCasesCount?: number;
  pubmedArticlesCount?: number;
}

export function AdvancedContext({
  caseSynthesis,
  pubmedSynthesis,
  similarCasesCount,
  pubmedArticlesCount
}: AdvancedContextProps) {
  const hasContent = caseSynthesis || pubmedSynthesis;

  if (!hasContent) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Stats */}
      <div className="flex gap-4">
        {similarCasesCount !== undefined && (
          <div className="glass-panel px-4 py-2 flex items-center gap-2">
            <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
            <span className="text-sm text-slate-600">
              <span className="font-semibold text-slate-800">{similarCasesCount}</span> similar cases
            </span>
          </div>
        )}

        {pubmedArticlesCount !== undefined && pubmedArticlesCount > 0 && (
          <div className="glass-panel px-4 py-2 flex items-center gap-2">
            <svg className="w-4 h-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
            <span className="text-sm text-slate-600">
              <span className="font-semibold text-slate-800">{pubmedArticlesCount}</span> PubMed articles
            </span>
          </div>
        )}
      </div>

      {/* Case Synthesis */}
      {caseSynthesis && (
        <GlassCard className="p-5" hover={false}>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center">
              <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
            </div>
            <h4 className="text-sm font-medium text-purple-700">Similar Cases Synthesis</h4>
          </div>
          <p className="text-slate-700 text-sm leading-relaxed whitespace-pre-wrap">
            {caseSynthesis}
          </p>
        </GlassCard>
      )}

      {/* PubMed Synthesis */}
      {pubmedSynthesis && (
        <GlassCard className="p-5" hover={false}>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center">
              <svg className="w-4 h-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
                />
              </svg>
            </div>
            <h4 className="text-sm font-medium text-amber-700">Literature Synthesis</h4>
          </div>
          <p className="text-slate-700 text-sm leading-relaxed whitespace-pre-wrap">
            {pubmedSynthesis}
          </p>
        </GlassCard>
      )}
    </motion.div>
  );
}
