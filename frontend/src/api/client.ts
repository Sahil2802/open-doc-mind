import type { Document, CitationMeta } from '../types';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

// ── Documents ─────────────────────────────────────────────────

export async function fetchDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/api/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  const data = await res.json();
  return data.documents;
}

export async function fetchDocument(id: string): Promise<Document> {
  const res = await fetch(`${API_BASE}/api/documents/${id}`);
  if (!res.ok) throw new Error('Document not found');
  return res.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/documents/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete document');
}

export async function uploadDocument(file: File): Promise<{ document_id: string; status: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/api/ingest`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? 'Upload failed');
  }
  return res.json();
}

// ── Query (SSE streaming) ─────────────────────────────────────

export interface QueryStreamCallbacks {
  onToken: (token: string) => void;
  onCitations: (citations: CitationMeta[]) => void;
  onReplace: (fullText: string) => void;
  onDone: () => void;
  onError: (message: string) => void;
}

export async function streamQuery(
  query: string,
  documentId: string | null,
  callbacks: QueryStreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, document_id: documentId }),
    signal,
  });

  if (!res.ok || !res.body) {
    callbacks.onError('Failed to connect to query endpoint');
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    let currentEvent = '';
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        const dataStr = line.slice(6).trim();
        try {
          const data = JSON.parse(dataStr);
          switch (currentEvent) {
            case 'token':
              callbacks.onToken(data.text);
              break;
            case 'citations':
              callbacks.onCitations(data);
              break;
            case 'replace':
              callbacks.onReplace(data.text);
              break;
            case 'done':
              callbacks.onDone();
              break;
            case 'error':
              callbacks.onError(data.message);
              break;
          }
        } catch {
          // Malformed JSON in stream — skip
        }
      }
    }
  }
}