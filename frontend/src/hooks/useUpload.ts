import { useState, useCallback } from 'react';
import { uploadDocument, fetchDocument } from '../api/client';
import type { UploadState } from '../types';

const ACCEPTED_TYPES = ['text/plain', 'application/pdf'];
const MAX_SIZE_BYTES = 50 * 1024 * 1024;

export function useUpload(onSuccess: (documentId: string) => void) {
  const [uploadState, setUploadState] = useState<UploadState>({
    status: 'idle',
    documentId: null,
    errorMessage: null,
    progress: 0,
  });

  const upload = useCallback(async (file: File) => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setUploadState(s => ({ ...s, status: 'error', errorMessage: 'Only PDF and .txt files are supported' }));
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      setUploadState(s => ({ ...s, status: 'error', errorMessage: 'File must be under 50MB' }));
      return;
    }

    setUploadState({ status: 'uploading', documentId: null, errorMessage: null, progress: 0 });

    try {
      const { document_id, status } = await uploadDocument(file);

      if (status === 'duplicate') {
        setUploadState({ status: 'done', documentId: document_id, errorMessage: null, progress: 100 });
        onSuccess(document_id);
        return;
      }

      // Poll for processing completion
      setUploadState(s => ({ ...s, status: 'processing', documentId: document_id, progress: 30 }));

      let attempts = 0;
      const maxAttempts = 60;

      const poll = async () => {
        const doc = await fetchDocument(document_id);
        if (doc.status === 'ready') {
          setUploadState({ status: 'done', documentId: document_id, errorMessage: null, progress: 100 });
          onSuccess(document_id);
        } else if (doc.status === 'failed') {
          setUploadState({ status: 'error', documentId: document_id, errorMessage: doc.error_message ?? 'Processing failed', progress: 0 });
        } else if (attempts < maxAttempts) {
          attempts++;
          const progress = Math.min(30 + (attempts / maxAttempts) * 60, 90);
          setUploadState(s => ({ ...s, progress }));
          setTimeout(poll, 2000);
        } else {
          setUploadState(s => ({ ...s, status: 'error', errorMessage: 'Processing timed out' }));
        }
      };

      setTimeout(poll, 2000);
    } catch (err) {
      setUploadState({ status: 'error', documentId: null, errorMessage: String(err), progress: 0 });
    }
  }, [onSuccess]);

  const reset = useCallback(() => {
    setUploadState({ status: 'idle', documentId: null, errorMessage: null, progress: 0 });
  }, []);

  return { uploadState, upload, reset };
}