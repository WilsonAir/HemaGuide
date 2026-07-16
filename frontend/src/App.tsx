import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from './components/layout/Header';
import { GlassCard } from './components/layout/GlassCard';
import { DropZone } from './components/upload/DropZone';
import { CaseTextInput } from './components/upload/CaseTextInput';
import { ConfigPanel } from './components/config/ConfigPanel';
import { StatusIndicator } from './components/status/StatusIndicator';
import { LogViewer } from './components/status/LogViewer';
import { InterimResults } from './components/status/InterimResults';
import { ResultsDisplay } from './components/results/ResultsDisplay';
import { useWebSocket } from './hooks/useWebSocket';
import * as api from './api/client';
import type { Config, ProcessingStatus, AgentResult, StatusUpdate, CaseResult } from './types/agent';

export default function App() {
  // State
  const [config, setConfig] = useState<Config>({
    llmMode: 'openai',
    decisionModel: 'qwen-plus',
  });
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [status, setStatus] = useState<ProcessingStatus>('idle');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const [currentCase, setCurrentCase] = useState<number>(0);
  const [totalCases, setTotalCases] = useState<number>(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [caseResults, setCaseResults] = useState<CaseResult[]>([]);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<'upload' | 'paste'>('upload');

  // WebSocket for real-time updates
  useWebSocket(jobId, {
    onMessage: useCallback((data: StatusUpdate) => {
      if (data.status) {
        setStatus(data.status as ProcessingStatus);
      }
      if (data.message) {
        setStatusMessage(data.message);
      }
      if (data.progress !== undefined) {
        setProgress(data.progress);
      }
      if (data.current_case !== undefined) {
        setCurrentCase(data.current_case);
      }
      if (data.total_cases !== undefined) {
        setTotalCases(data.total_cases);
      }
      // Handle single log entry (streaming)
      if (data.log) {
        setLogs(prev => {
          const newLogs = [...prev, data.log!];
          // Keep last 100 logs
          return newLogs.slice(-100);
        });
      }
      // Handle bulk logs (initial load or error)
      if (data.logs && data.logs.length > 0) {
        setLogs(data.logs);
      }
      // Bulk case results (initial WS frame on reconnect — server is source of truth)
      if (data.case_results && data.case_results.length > 0) {
        setCaseResults(data.case_results);
      }
      // Handle interim case result
      if (data.case_result) {
        setCaseResults(prev => {
          // Avoid duplicates
          if (prev.some(cr => cr.case_id === data.case_result!.case_id)) {
            return prev;
          }
          return [...prev, data.case_result!];
        });
      }
      if (data.result) {
        setResult(data.result);
        setJobId(null);
      }
    }, []),
    onError: useCallback(() => {
      setError('WebSocket connection failed');
    }, []),
  });

  // Load existing files on mount
  useEffect(() => {
    api.listFiles().then(files => {
      setUploadedFiles(files);
    }).catch(console.error);
  }, []);

  // Handle file upload
  const handleFilesAccepted = useCallback(async (files: File[]) => {
    setError(null);
    setStatus('uploading');
    setStatusMessage('Uploading files...');

    try {
      for (const file of files) {
        await api.uploadFile(file);
      }
      const updatedFiles = await api.listFiles();
      setUploadedFiles(updatedFiles);
      setStatus('idle');
      setStatusMessage('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setStatus('error');
    }
  }, []);

  // Handle file removal
  const handleRemoveFile = useCallback(async (filename: string) => {
    try {
      await api.deleteFile(filename);
      setUploadedFiles(prev => prev.filter(f => f !== filename));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  }, []);

  const handleTextAdd = useCallback(async (text: string, filename?: string) => {
    setError(null);
    setStatus('uploading');
    setStatusMessage('Saving case text...');
    try {
      await api.uploadText(text, filename);
      const updatedFiles = await api.listFiles();
      setUploadedFiles(updatedFiles);
      setStatus('idle');
      setStatusMessage('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save case text');
      setStatus('error');
      throw err instanceof Error ? err : new Error('Failed to save case text');
    }
  }, []);

  const handleTextParse = useCallback(async (text: string, filename?: string) => {
    setError(null);
    setStatus('extracting');
    setStatusMessage('Parsing case text...');
    setProgress(15);
    try {
      const response = await api.parseText(text, {
        filename,
        llmMode: config.llmMode,
        forceExtract: true,
      });
      const updatedFiles = await api.listFiles();
      setUploadedFiles(updatedFiles);
      setStatus('idle');
      setStatusMessage('');
      setProgress(0);
      return {
        filename: response.filename,
        entity_slug: response.extracted?.entity_slug,
        sections: response.extracted?.sections,
        document_id: response.extracted?.document_id,
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Parsing failed';
      setError(message);
      setStatus('error');
      setProgress(0);
      throw err instanceof Error ? err : new Error(message);
    }
  }, [config.llmMode]);

  // Handle process start
  const handleProcess = useCallback(async () => {
    if (uploadedFiles.length === 0) {
      setError('Please upload or paste a case first');
      return;
    }

    setError(null);
    setResult(null);
    setLogs([]);
    setCaseResults([]);
    setCurrentCase(0);
    setTotalCases(uploadedFiles.length);
    setStatus('extracting');
    setStatusMessage('Starting processing...');
    setProgress(0);

    try {
      const response = await api.startProcessing(uploadedFiles, config);
      setJobId(response.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
      setStatus('error');
    }
  }, [uploadedFiles, config]);

  const isProcessing = !['idle', 'complete', 'error'].includes(status);

  return (
    <div className="min-h-screen relative bg-gradient-to-b from-slate-50 to-slate-100">
      {/* Main content */}
      <div className="relative z-10 container mx-auto px-4 py-8 max-w-4xl">
        <Header />

        <div className="grid gap-6">
          {/* Case input: upload .docx/.txt or paste plain text */}
          <section className="space-y-4">
            <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
              <button
                type="button"
                onClick={() => setInputMode('upload')}
                disabled={isProcessing}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  inputMode === 'upload'
                    ? 'bg-hemaguide-500 text-white'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                Upload file
              </button>
              <button
                type="button"
                onClick={() => setInputMode('paste')}
                disabled={isProcessing}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  inputMode === 'paste'
                    ? 'bg-hemaguide-500 text-white'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                Paste text
              </button>
            </div>

            {inputMode === 'upload' ? (
              <DropZone
                onFilesAccepted={handleFilesAccepted}
                uploadedFiles={uploadedFiles}
                onRemoveFile={handleRemoveFile}
                isProcessing={isProcessing}
              />
            ) : (
              <>
                <CaseTextInput
                  disabled={isProcessing}
                  onAdd={handleTextAdd}
                  onParse={handleTextParse}
                />
                {uploadedFiles.length > 0 && (
                  <div className="glass-panel p-4">
                    <h4 className="text-sm font-medium text-slate-600 mb-3">
                      Queued cases ({uploadedFiles.length})
                    </h4>
                    <div className="space-y-2">
                      {uploadedFiles.map((filename) => (
                        <div
                          key={filename}
                          className="flex items-center justify-between py-2 px-3 rounded-lg bg-slate-50 border border-slate-200"
                        >
                          <span className="text-sm text-slate-700 font-medium">{filename}</span>
                          {!isProcessing && (
                            <button
                              type="button"
                              onClick={() => handleRemoveFile(filename)}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50"
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </section>

          {/* Config & Actions */}
          <section className="grid md:grid-cols-2 gap-6">
            <ConfigPanel
              config={config}
              onConfigChange={setConfig}
              disabled={isProcessing}
            />

            <GlassCard className="p-5 flex flex-col" hover={false}>
              <h3 className="text-base font-medium text-slate-800 mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-hemaguide-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                  />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Processing
              </h3>

              <div className="flex-1 flex flex-col justify-between">
                <p className="text-sm text-slate-500 mb-4">
                  {uploadedFiles.length === 0
                    ? 'Upload a file or paste case text to continue'
                    : `${uploadedFiles.length} case${uploadedFiles.length !== 1 ? 's' : ''} ready for processing`
                  }
                </p>

                <motion.button
                  onClick={handleProcess}
                  disabled={isProcessing || uploadedFiles.length === 0}
                  className="glass-button-primary w-full py-3.5"
                  whileHover={{ scale: isProcessing ? 1 : 1.02 }}
                  whileTap={{ scale: isProcessing ? 1 : 0.98 }}
                >
                  {isProcessing ? (
                    <span className="flex items-center justify-center gap-2">
                      <motion.svg
                        className="w-5 h-5"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </motion.svg>
                      Processing...
                    </span>
                  ) : (
                    'Start Agent'
                  )}
                </motion.button>
              </div>
            </GlassCard>
          </section>

          {/* Status */}
          <AnimatePresence>
            {status !== 'idle' && (
              <motion.section
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <StatusIndicator
                  status={status}
                  message={statusMessage}
                  progress={progress}
                  currentCase={currentCase}
                  totalCases={totalCases}
                />
              </motion.section>
            )}
          </AnimatePresence>

          {/* Interim Results - Show during processing */}
          <AnimatePresence>
            {caseResults.length > 0 && (
              <motion.section
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <InterimResults
                  caseResults={caseResults}
                  isProcessing={isProcessing}
                />
              </motion.section>
            )}
          </AnimatePresence>

          {/* Log Viewer */}
          <AnimatePresence>
            {logs.length > 0 && (
              <motion.section
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <LogViewer logs={logs} isExpanded={isProcessing} />
              </motion.section>
            )}
          </AnimatePresence>

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <GlassCard variant="error" className="p-4" hover={false}>
                  <div className="flex items-center gap-3">
                    <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <span className="text-red-700">{error}</span>
                    <button
                      onClick={() => setError(null)}
                      className="ml-auto p-1 hover:bg-red-100 rounded-lg transition-colors"
                    >
                      <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </GlassCard>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Final Results - Only show when complete and no interim results shown */}
          <AnimatePresence>
            {result && status === 'complete' && caseResults.length === 0 && (
              <motion.section
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
              >
                <div className="mb-4 flex items-center gap-2">
                  <div className="h-px flex-1 bg-gradient-to-r from-transparent via-hemaguide-300 to-transparent" />
                  <span className="text-sm text-slate-400 px-4">Result</span>
                  <div className="h-px flex-1 bg-gradient-to-r from-transparent via-hemaguide-300 to-transparent" />
                </div>
                <ResultsDisplay result={result} />
              </motion.section>
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <footer className="mt-12 text-center text-xs text-slate-400">
          <p>HemaGuide - Research Use Only</p>
        </footer>
      </div>
    </div>
  );
}
