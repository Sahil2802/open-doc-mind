import type { Message } from '../types';
import { CitationCard } from './CitationCard';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isRefused = message.wasRefused;

  return (
    <div className={`animate-slide-up ${isUser ? 'ml-auto' : 'mr-auto'} max-w-[85%]`}>
      <div
        className={`
          rounded-2xl px-5 py-3
          ${isUser
            ? 'bg-ink text-parchment ml-auto rounded-br-md'
            : isRefused
              ? 'bg-amber/20 text-ink border border-amber/30'
              : 'bg-white text-ink border border-gray-100 rounded-bl-md'
          }
        `}
      >
        {isRefused && (
          <div className="flex items-center gap-2 mb-2 text-amber-dark">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-xs font-medium">Unable to answer</span>
          </div>
        )}
        <p className={`whitespace-pre-wrap leading-relaxed ${message.isStreaming && !isUser ? 'streaming-cursor' : ''}`}>
          {message.text}
        </p>
      </div>

      {/* Citations - only show for assistant messages that aren't refused */}
      {!isUser && !isRefused && message.citations.length > 0 && !message.isStreaming && (
        <div className="mt-2 space-y-2">
          {message.citations.map((citation, idx) => (
            <CitationCard key={`${citation.pinecone_id}-${idx}`} citation={citation} />
          ))}
        </div>
      )}
    </div>
  );
}