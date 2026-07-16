import { useCallback, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';

interface DropZoneProps {
  onFilesAccepted: (files: File[]) => void;
  uploadedFiles: string[];
  onRemoveFile: (filename: string) => void;
  isProcessing: boolean;
}

export function DropZone({
  onFilesAccepted,
  uploadedFiles,
  onRemoveFile,
  isProcessing
}: DropZoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const caseFiles = acceptedFiles.filter(
      f =>
        (f.name.endsWith('.docx') || f.name.endsWith('.txt')) &&
        !f.name.startsWith('~')
    );
    if (caseFiles.length > 0) {
      onFilesAccepted(caseFiles);
    }
    setIsDragActive(false);
  }, [onFilesAccepted]);

  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    disabled: isProcessing,
    onDragEnter: () => setIsDragActive(true),
    onDragLeave: () => setIsDragActive(false),
  });

  return (
    <div className="space-y-4">
      <motion.div
        className={`drop-zone ${isDragActive ? 'drop-zone-active' : ''}`}
        whileHover={{ scale: isProcessing ? 1 : 1.01 }}
        whileTap={{ scale: isProcessing ? 1 : 0.99 }}
        animate={{
          borderColor: isDragActive ? 'rgba(6, 182, 212, 0.6)' : 'rgba(203, 213, 225, 1)'
        }}
      >
        <div
          {...getRootProps()}
          className="flex flex-col items-center justify-center min-h-[180px] text-center"
        >
          <input {...getInputProps()} />

          <motion.div
            animate={{
              scale: isDragActive ? 1.15 : 1,
              rotate: isDragActive ? [0, -8, 8, 0] : 0,
              y: isDragActive ? -5 : 0
            }}
            transition={{ duration: 0.3 }}
            className="mb-4"
          >
            <svg
              className={`w-14 h-14 transition-colors duration-300 ${
                isDragActive ? 'text-hemaguide-500' : 'text-slate-400'
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </motion.div>

          <h3 className={`text-lg font-medium mb-2 transition-colors ${
            isDragActive ? 'text-hemaguide-600' : 'text-slate-700'
          }`}>
            {isDragActive ? 'Drop document here' : 'Upload Tumor Board Document'}
          </h3>
          <p className="text-sm text-slate-500">
            .docx or .txt via Drag & Drop or Click
          </p>

          {isProcessing && (
            <motion.p
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-3 text-hemaguide-600 text-sm font-medium"
            >
              Processing...
            </motion.p>
          )}
        </div>
      </motion.div>

      {/* Uploaded files list */}
      <AnimatePresence mode="popLayout">
        {uploadedFiles.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="glass-panel p-4"
          >
            <h4 className="text-sm font-medium text-slate-600 mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              Uploaded Files ({uploadedFiles.length})
            </h4>
            <div className="space-y-2">
              {uploadedFiles.map((filename, index) => (
                <motion.div
                  key={filename}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center justify-between py-2 px-3 rounded-lg bg-slate-50 border border-slate-200 group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-hemaguide-50 flex items-center justify-center">
                      <svg className="w-4 h-4 text-hemaguide-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <span className="text-sm text-slate-700 font-medium">{filename}</span>
                  </div>
                  {!isProcessing && (
                    <button
                      onClick={() => onRemoveFile(filename)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
