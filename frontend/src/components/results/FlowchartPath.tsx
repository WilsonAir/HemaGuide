import { motion } from 'framer-motion';
import { GlassCard } from '../layout/GlassCard';

interface FlowchartPathProps {
  path: string;
}

export function FlowchartPath({ path }: FlowchartPathProps) {
  // Split path by arrows or similar delimiters
  const steps = path.split(/\s*[→\->]+\s*/).filter(Boolean);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <GlassCard className="p-5" hover={false}>
        <div className="flex items-center gap-2 mb-4">
          <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
            />
          </svg>
          <span className="text-sm font-medium text-slate-600">Flowchart Path</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {steps.map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="flex items-center gap-2"
            >
              <div className={`
                px-3 py-2 rounded-lg text-sm
                ${index === steps.length - 1
                  ? 'bg-emerald-50 border border-emerald-200 text-emerald-700 font-medium'
                  : 'bg-slate-50 border border-slate-200 text-slate-700'
                }
              `}>
                {step.trim()}
              </div>

              {index < steps.length - 1 && (
                <svg className="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              )}
            </motion.div>
          ))}
        </div>
      </GlassCard>
    </motion.div>
  );
}
