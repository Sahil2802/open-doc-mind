import { useState, useEffect, useCallback } from 'react';
import { StatusBar } from './components/StatusBar';
import { UploadPanel } from './components/UploadPanel';
import { ChatWindow } from './components/ChatWindow';
import { useChat } from './hooks/useChat';
import { useUpload } from './hooks/useUpload';
import { fetchDocuments, deleteDocument } from './api/client';
import type { Document } from './types';

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  const { messages, isLoading, sendMessage, stopStreaming, clearMessages } = useChat(selectedDocId);

  const handleUploadSuccess = useCallback(() => {
    loadDocuments();
  }, []);

  const { uploadState, upload, reset } = useUpload(handleUploadSuccess);

  const loadDocuments = useCallback(async () => {
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleDeleteDocument = async (id: string) => {
    try {
      await deleteDocument(id);
      setDocuments(prev => prev.filter(d => d.id !== id));
      if (selectedDocId === id) {
        setSelectedDocId(null);
      }
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const handleToggleScope = (docId: string | null) => {
    setSelectedDocId(docId);
  };

  const scopeLabel = selectedDocId
    ? documents.find(d => d.id === selectedDocId)?.file_name ?? 'all'
    : 'all';

  return (
    <div className="h-screen flex flex-col">
      <StatusBar
        scope={scopeLabel}
        onClear={clearMessages}
        onToggleScope={handleToggleScope}
        documents={documents}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-80 flex-shrink-0 border-r border-gray-200">
          <UploadPanel
            documents={documents}
            uploadState={uploadState}
            onUpload={upload}
            onDelete={handleDeleteDocument}
            onReset={reset}
          />
        </aside>

        {/* Main chat area */}
        <main className="flex-1">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSendMessage={sendMessage}
            onStopStreaming={stopStreaming}
          />
        </main>
      </div>
    </div>
  );
}

export default App;