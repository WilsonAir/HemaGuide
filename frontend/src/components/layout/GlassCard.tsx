import { motion, HTMLMotionProps } from 'framer-motion';
import { ReactNode } from 'react';

interface GlassCardProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
  children: ReactNode;
  variant?: 'default' | 'highlight' | 'success' | 'error';
  hover?: boolean;
  glow?: boolean;
}

export function GlassCard({
  children,
  variant = 'default',
  hover = true,
  glow = false,
  className = '',
  ...props
}: GlassCardProps) {
  const variants = {
    default: 'border-slate-200',
    highlight: 'border-hemaguide-200 bg-hemaguide-50',
    success: 'border-emerald-200 bg-emerald-50',
    error: 'border-red-200 bg-red-50',
  };

  const glowClass = glow ? 'shadow-hemaguide-glow' : '';
  const hoverClass = hover ? 'glass-panel-hover' : '';

  return (
    <motion.div
      className={`glass-panel ${variants[variant]} ${hoverClass} ${glowClass} ${className}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      {...props}
    >
      {children}
    </motion.div>
  );
}
