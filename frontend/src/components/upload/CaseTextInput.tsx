import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassCard } from '../layout/GlassCard';

export interface ParsedCasePreview {
  filename: string;
  entity_slug?: string;
  sections?: Record<string, unknown>;
  document_id?: string;
}

interface CaseTextInputProps {
  disabled?: boolean;
  onAdd: (text: string, filename?: string) => Promise<void>;
  onParse: (text: string, filename?: string) => Promise<ParsedCasePreview>;
}

const PREVIEW_FIELDS: { key: string; label: string }[] = [
  { key: 'entity', label: 'Entity' },
  { key: 'age', label: 'Age' },
  { key: 'ECOG', label: 'ECOG' },
  { key: 'main_diagnosis', label: 'Main diagnosis' },
  { key: 'secondary_diagnoses', label: 'Secondary diagnoses' },
  { key: 'history', label: 'History / course' },
  { key: 'question', label: 'Question' },
  { key: 'decision', label: 'Prior decision (if any)' },
  { key: 'predictive_factors', label: 'Predictive factors' },
  { key: 'prior_treatments', label: 'Prior treatments' },
  { key: 'mol_info', label: 'Molecular info' },
];

function formatSectionValue(value: unknown): string {
  if (value == null || value === '') return '—';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function CaseTextInput({ disabled, onAdd, onParse }: CaseTextInputProps) {
  const [text, setText] = useState('');
  const [filename, setFilename] = useState('');
  const [busy, setBusy] = useState<'add' | 'parse' | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [preview, setPreview] = useState<ParsedCasePreview | null>(null);

  const canSubmit = text.trim().length > 0 && !disabled && !busy;

  const handleAdd = async () => {
    if (!canSubmit) return;
    setLocalError(null);
    setBusy('add');
    try {
      await onAdd(text.trim(), filename.trim() || undefined);
      setText('');
      setFilename('');
      setPreview(null);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Failed to add case text');
    } finally {
      setBusy(null);
    }
  };

  const handleParse = async () => {
    if (!canSubmit) return;
    setLocalError(null);
    setBusy('parse');
    try {
      const result = await onParse(text.trim(), filename.trim() || undefined);
      setPreview(result);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Parsing failed');
      setPreview(null);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-4">
      <GlassCard className="p-5" hover={false}>
        <h3 className="text-base font-medium text-slate-800 mb-1 flex items-center gap-2">
          <svg className="w-5 h-5 text-hemaguide-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
            />
          </svg>
          Paste case text
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Paste a tumor-board vignette as plain text. Parse runs extraction directly — no Word conversion.
        </p>

        <label className="block text-xs font-medium text-slate-500 mb-1">
          Filename (optional)
        </label>
        <input
          type="text"
          value={filename}
          onChange={(e) => setFilename(e.target.value)}
          disabled={disabled || !!busy}
          placeholder="e.g. aml_case_paste"
          className="w-full mb-3 px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-hemaguide-300 disabled:opacity-50"
        />

        <label className="block text-xs font-medium text-slate-500 mb-1">
          Case text
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={disabled || !!busy}
          rows={12}
          placeholder={`Age: 51\nECOG: 1\nPrimary diagnosis:\nAcute myeloid leukemia...\nQuestion for the tumor board:\nTreatment initiation?\n...`}
          className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm text-slate-700 font-mono placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-hemaguide-300 disabled:opacity-50 resize-y min-h-[200px]"
        />

        <div className="mt-4 flex flex-col sm:flex-row gap-3">
          <motion.button
            type="button"
            onClick={handleAdd}
            disabled={!canSubmit}
            className="glass-button flex-1 py-2.5 text-sm"
            whileHover={{ scale: canSubmit ? 1.01 : 1 }}
            whileTap={{ scale: canSubmit ? 0.99 : 1 }}
          >
            {busy === 'add' ? 'Adding…' : 'Add to queue'}
          </motion.button>
          <motion.button
            type="button"
            onClick={handleParse}
            disabled={!canSubmit}
            className="glass-button-primary flex-1 py-2.5 text-sm"
            whileHover={{ scale: canSubmit ? 1.01 : 1 }}
            whileTap={{ scale: canSubmit ? 0.99 : 1 }}
          >
            {busy === 'parse' ? (
              <span className="flex items-center justify-center gap-2">
                <motion.svg
                  className="w-4 h-4"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </motion.svg>
                Parsing…
              </span>
            ) : (
              'Parse case'
            )}
          </motion.button>
        </div>

        {localError && (
          <p className="mt-3 text-sm text-red-600">{localError}</p>
        )}
      </GlassCard>

      <AnimatePresence>
        {preview && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            <GlassCard className="p-5" hover={false} variant="highlight">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <h4 className="text-sm font-semibold text-slate-800">Parsed extraction</h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Saved as <span className="font-medium text-slate-700">{preview.filename}</span>
                    {preview.entity_slug ? (
                      <> · entity <span className="font-medium text-slate-700">{preview.entity_slug}</span></>
                    ) : null}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setPreview(null)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-white/60"
                  aria-label="Dismiss preview"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                {PREVIEW_FIELDS.map(({ key, label }) => {
                  const value = preview.sections?.[key];
                  if (value == null || value === '') return null;
                  return (
                    <div key={key} className="rounded-lg bg-white/70 border border-slate-200 px-3 py-2">
                      <div className="text-xs font-medium text-slate-500 mb-1">{label}</div>
                      <pre className="text-sm text-slate-800 whitespace-pre-wrap font-sans leading-relaxed">
                        {formatSectionValue(value)}
                      </pre>
                    </div>
                  );
                })}
              </div>
              <p className="mt-3 text-xs text-slate-500">
                The case is also in the upload queue — click Start Agent to run a full decision.
              </p>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
