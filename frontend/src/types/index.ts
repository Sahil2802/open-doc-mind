export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed';

export interface Document {
  id: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  chunk_count: number;
  page_count: number | null;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
}

export interface CitationMeta {
  excerpt_number: number;
  file_name: string;
  page_number: number | null;
  chunk_index: number;
  pinecone_id: string;
  score: number | null;              // Final normalized relevance score
  reranker_score: number | null;     // Raw cross-encoder score
}

export type MessageRole = 'user' | 'assistant';

export interface Message {
  id: string;
  role: MessageRole;
  text: string;
  citations: CitationMeta[];
  isStreaming: boolean;
  wasRefused: boolean;
  timestamp: Date;
}

export interface UploadState {
  status: 'idle' | 'uploading' | 'processing' | 'done' | 'error';
  documentId: string | null;
  errorMessage: string | null;
  progress: number;
}