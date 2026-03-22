import { useState, useCallback, DragEvent, useRef } from 'react';
import type { Document, UploadState } from '../types';

interface UploadPanelProps {
  documents: Document[];
  uploadState: UploadState;
  onUpload: (file: File) => void;
  onDelete: (id: string) => void;
  onReset: () => void;
}

export function UploadPanel({ documents, uploadState, onUpload, onDelete, onReset }: UploadPanelProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      onUpload(files[0]);
    }
  }, [onUpload]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onUpload(files[0]);
    }
  }, [onUpload]);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusIcon = (status: Document['status']) => {
    switch (status) {
      case 'ready':
        return (
          <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </span>
        );
      case 'processing':
        return (
          <span className="w-6 h-6 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center animate-pulse">
            <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </span>
        );
      case 'pending':
        return (
          <span className="w-6 h-6 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </span>
        );
      case 'failed':
        return (
          <span className="w-6 h-6 rounded-full bg-red-100 text-red-600 flex items-center justify-center">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </span>
        );
    }
  };

  return (
    <div className="h-full bg-ink text-parchment flex flex-col">
      {/* Header */}
      <div className="p-5 border-b border-ink-light">
        <h2 className="font-display text-lg font-semibold">Documents</h2>
      </div>

      {/* Upload zone */}
      <div className="p-4">
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`
            border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all
            ${isDragging
              ? 'border-gold bg-gold/10'
              : 'border-ink-light hover:border-amber hover:bg-ink-light/30'
            }
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt"
            onChange={handleFileSelect}
            className="hidden"
          />
          <svg className="w-8 h-8 mx-auto mb-2 text-parchment-dark/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-sm text-parchment-dark/70">
            Drop files here or click to upload
          </p>
          <p className="text-xs text-parchment-dark/40 mt-1">
            PDF or .txt, max 50MB
          </p>
        </div>

        {/* Upload progress/error */}
        {(uploadState.status === 'uploading' || uploadState.status === 'processing' || uploadState.status === 'error') && (
          <div className="mt-4 animate-fade-in">
            {uploadState.status === 'error' ? (
              <div className="bg-red-900/30 border border-red-800 rounded-lg p-3">
                <p className="text-red-400 text-sm">{uploadState.errorMessage}</p>
                <button
                  onClick={onReset}
                  className="mt-2 text-xs text-red-400 hover:text-red-300 underline"
                >
                  Try again
                </button>
              </div>
            ) : (
              <div className="bg-ink-light rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-parchment-dark">
                    {uploadState.status === 'uploading' ? 'Uploading...' : 'Processing...'}
                  </span>
                  <span className="text-sm text-gold">{Math.round(uploadState.progress)}%</span>
                </div>
                <div className="h-1.5 bg-ink rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gold transition-all duration-500"
                    style={{ width: `${uploadState.progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <div className="space-y-2">
          {documents.map(doc => (
            <div
              key={doc.id}
              className="group bg-ink-light/50 hover:bg-ink-light rounded-lg p-3 transition-colors"
            >
              <div className="flex items-start gap-3">
                {getStatusIcon(doc.status)}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-parchment truncate">{doc.file_name}</p>
                  <div className="flex items-center gap-2 mt-1 text-xs text-parchment-dark/50">
                    <span>{formatFileSize(doc.file_size)}</span>
                    {doc.chunk_count > 0 && (
                      <>
                        <span>•</span>
                        <span>{doc.chunk_count} chunks</span>
                      </>
                    )}
                    {doc.page_count !== null && (
                      <>
                        <span>•</span>
                        <span>{doc.page_count} pages</span>
                      </>
                    )}
                  </div>
                  {doc.status === 'failed' && doc.error_message && (
                    <p className="text-xs text-red-400 mt-2">{doc.error_message}</p>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(doc.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-ink rounded transition-all text-parchment-dark/50 hover:text-red-400"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>

        {documents.length === 0 && (
          <div className="text-center py-8 text-parchment-dark/40">
            <p className="text-sm">No documents yet</p>
          </div>
        )}
      </div>
    </div>
  );
}