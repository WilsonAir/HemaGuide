import { motion, AnimatePresence } from 'framer-motion';
import { GlassCard } from '../layout/GlassCard';
import { DecisionCard } from './DecisionCard';
import { MolecularReport } from './MolecularReport';
import { AdvancedContext } from './AdvancedContext';
import { FlowchartPath } from './FlowchartPath';
import type { AgentResult } from '../../types/agent';

interface ResultsDisplayProps {
  result: AgentResult | null;
}

export function ResultsDisplay({ result }: ResultsDisplayProps) {
  if (!result) return null;

  const modeConfig = {
    GUIDELINE: {
      label: 'PROTOCOL',
      color: 'mode-badge-guideline',
      description: 'Protocol Mode - Clinical Pathways'
    },
    ADVANCED: {
      label: 'SYNTHESIS',
      color: 'mode-badge-advanced',
      description: 'Synthesis Mode - SA-RAG + PubMed'
    },
    MOLECULAR: {
      label: 'CLASSIFICATION',
      color: 'mode-badge-molecular',
      description: 'Classification Mode - Horak SOP'
    }
  };

  const mode = modeConfig[result.mode] || modeConfig.GUIDELINE;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header with mode badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className={`mode-badge ${mode.color}`}
          >
            {mode.label}
          </motion.span>
          <span className="text-slate-500 text-sm">{mode.description}</span>
        </div>

        {result.source_file && (
          <span className="text-sm text-slate-400">
            Source: {result.source_file}
          </span>
        )}
      </div>

      {/* Diagnosis context */}
      {result.input_diagnosis && (
        <GlassCard className="p-4" hover={false}>
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-slate-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <div>
              <span className="text-xs text-slate-500 uppercase tracking-wider">Input Diagnosis</span>
              <p className="text-sm text-slate-700 mt-1 whitespace-pre-wrap">{result.input_diagnosis}</p>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Main Decision - Konferenzbeschluss */}
      <DecisionCard
        title="Decision"
        content={result.konferenzbeschluss}
        variant="highlight"
        icon="decision"
      />

      {/* Reasoning */}
      <DecisionCard
        title="Reasoning"
        content={result.begründung}
        variant="default"
        icon="reason"
      />

      {/* Routing Reasoning */}
      {result.routing_reasoning && (
        <GlassCard className="p-5" hover={false}>
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M13 9l3 3m0 0l-3 3m3-3H8m13 0a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-medium text-slate-500 mb-2">Routing Reasoning</h3>
              <p className="text-slate-700 text-sm leading-relaxed whitespace-pre-wrap">
                {result.routing_reasoning}
              </p>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Mode-specific content */}
      <AnimatePresence>
        {result.mode === 'GUIDELINE' && result.flowchart_path && (
          <FlowchartPath path={result.flowchart_path} />
        )}

        {result.mode === 'ADVANCED' && (
          <AdvancedContext
            caseSynthesis={result.case_synthesis}
            pubmedSynthesis={result.pubmed_synthesis}
            similarCasesCount={result.similar_cases_count || result.similar_cases_used}
            pubmedArticlesCount={result.pubmed_articles_count}
          />
        )}

        {result.mode === 'MOLECULAR' && result.classification_results && (
          <MolecularReport
            results={result.classification_results}
            reportText={result.report_text}
          />
        )}
      </AnimatePresence>

      {/* Metadata footer */}
      <GlassCard className="p-4" hover={false}>
        <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
          {result.model && (
            <span>Model: {result.model}</span>
          )}
          {result.metadata?.tokens_used && (
            <span>Tokens: {result.metadata.tokens_used.toLocaleString()}</span>
          )}
          {result.extraction_timestamp && (
            <span>
              Timestamp: {new Date(result.extraction_timestamp).toLocaleString('en-US')}
            </span>
          )}
        </div>
      </GlassCard>
    </motion.div>
  );
}
