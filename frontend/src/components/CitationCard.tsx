import type { CitationMeta } from '../types';

interface CitationCardProps {
  citation: CitationMeta;
}

export function CitationCard({ citation }: CitationCardProps) {
  // Use the normalized `score` field (set by the retrieval layer to the most
  // authoritative relevance metric). Falls back to `reranker_score`.
  // Cross-encoder (ms-marco-MiniLM) outputs logits in range ~[-11, +11],
  // NOT cosine similarity [0, 1]. Thresholds calibrated accordingly.
  const score = citation.score ?? citation.reranker_score;
  const confidence = score !== null
    ? score >= 5 ? 'high' : score >= 1 ? 'medium' : 'low'
    : 'unknown';

  const confidenceColors = {
    high: 'bg-emerald-100 text-emerald-800',
    medium: 'bg-amber-100 text-amber-800',
    low: 'bg-gray-100 text-gray-600',
    unknown: 'bg-gray-100 text-gray-500',
  };

  const confidenceLabels = {
    high: 'Excellent match',
    medium: 'Good match',
    low: 'Weak match',
    unknown: 'Unknown',
  };

  return (
    <div className="bg-parchment-dark border border-gray-200 rounded-lg p-3 text-sm animate-fade-in">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-amber flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="font-medium text-ink truncate">{citation.file_name}</span>
          </div>
          <div className="mt-1 text-ink-light/70 flex items-center gap-2 text-xs">
            {citation.page_number !== null && (
              <span>Page {citation.page_number}</span>
            )}
            {citation.page_number !== null && citation.excerpt_number > 0 && (
              <span className="text-gray-400">•</span>
            )}
            {citation.excerpt_number > 0 && (
              <span>Excerpt #{citation.excerpt_number}</span>
            )}
          </div>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${confidenceColors[confidence]}`}>
          {confidenceLabels[confidence]}
        </span>
      </div>
    </div>
  );
}