import { motion } from 'framer-motion';
import { GlassCard } from '../layout/GlassCard';

interface DecisionCardProps {
  title: string;
  content: string;
  variant?: 'default' | 'highlight';
  icon?: 'decision' | 'reason';
}

export function DecisionCard({
  title,
  content,
  variant = 'default',
  icon = 'reason'
}: DecisionCardProps) {
  return (
    <GlassCard
      variant={variant}
      glow={variant === 'highlight'}
      className="p-6"
      hover={false}
    >
      <div className="flex items-start gap-4">
        <div className={`
          w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0
          ${variant === 'highlight'
            ? 'bg-hemaguide-100 border border-hemaguide-200'
            : 'bg-slate-100 border border-slate-200'
          }
        `}>
          {icon === 'decision' ? (
            <svg
              className={`w-5 h-5 ${variant === 'highlight' ? 'text-hemaguide-600' : 'text-slate-500'}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          ) : (
            <svg
              className={`w-5 h-5 ${variant === 'highlight' ? 'text-hemaguide-600' : 'text-slate-500'}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <h3 className={`text-sm font-medium mb-2 ${
            variant === 'highlight' ? 'text-hemaguide-700' : 'text-slate-500'
          }`}>
            {title}
          </h3>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-slate-800 leading-relaxed whitespace-pre-wrap"
          >
            {content}
          </motion.p>
        </div>
      </div>
    </GlassCard>
  );
}
