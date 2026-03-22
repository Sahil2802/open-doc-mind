import { useState, useRef, useEffect, FormEvent } from 'react';
import type { Message } from '../types';
import { MessageBubble } from './MessageBubble';

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (query: string) => void;
  onStopStreaming: () => void;
}

export function ChatWindow({ messages, isLoading, onSendMessage, onStopStreaming }: ChatWindowProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col h-full bg-parchment">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 mb-4 rounded-full bg-parchment-dark flex items-center justify-center">
              <svg className="w-8 h-8 text-ink-light" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h2 className="font-display text-2xl text-ink mb-2">Ask anything</h2>
            <p className="text-ink-light/60 max-w-sm">
              Upload documents and ask questions about their content. I'll search through them and provide citations.
            </p>
          </div>
        ) : (
          messages.map(message => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 border-t border-gray-100 bg-white/50 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your documents..."
            className="flex-1 resize-none rounded-xl border border-gray-200 bg-white px-4 py-3 text-ink placeholder:text-ink-light/50 focus:border-gold focus:ring-1 focus:ring-gold/30 transition-all"
            rows={1}
            style={{ minHeight: '48px', maxHeight: '120px' }}
            disabled={isLoading}
          />
          {isLoading ? (
            <button
              type="button"
              onClick={onStopStreaming}
              className="px-5 py-3 rounded-xl bg-amber text-white font-medium hover:bg-amber-dark transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="1" />
              </svg>
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="px-5 py-3 rounded-xl bg-ink text-parchment font-medium hover:bg-ink-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
              Send
            </button>
          )}
        </form>
      </div>
    </div>
  );
}