import { useState, useCallback, useRef } from 'react';
import { streamQuery } from '../api/client';
import type { Message, CitationMeta } from '../types';
import { nanoid } from 'nanoid';

export function useChat(selectedDocumentId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (query: string) => {
    if (!query.trim() || isLoading) return;

    // Add user message
    const userMsg: Message = {
      id: nanoid(),
      role: 'user',
      text: query,
      citations: [],
      isStreaming: false,
      wasRefused: false,
      timestamp: new Date(),
    };

    // Add placeholder assistant message
    const assistantId = nanoid();
    const assistantMsg: Message = {
      id: assistantId,
      role: 'assistant',
      text: '',
      citations: [],
      isStreaming: true,
      wasRefused: false,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setIsLoading(true);

    abortRef.current = new AbortController();

    await streamQuery(
      query,
      selectedDocumentId,
      {
        onToken: (token) => {
          setMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, text: m.text + token }
              : m
          ));
        },
        onCitations: (citations: CitationMeta[]) => {
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? { ...m, citations } : m
          ));
        },
        onReplace: (fullText: string) => {
          setMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, text: fullText, wasRefused: true }
              : m
          ));
        },
        onDone: () => {
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? { ...m, isStreaming: false } : m
          ));
          setIsLoading(false);
        },
        onError: (message: string) => {
          setMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, text: message, isStreaming: false, wasRefused: true }
              : m
          ));
          setIsLoading(false);
        },
      },
      abortRef.current.signal,
    );
  }, [isLoading, selectedDocumentId]);

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    setIsLoading(false);
    setMessages(prev => prev.map(m =>
      m.isStreaming ? { ...m, isStreaming: false } : m
    ));
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, isLoading, sendMessage, stopStreaming, clearMessages };
}