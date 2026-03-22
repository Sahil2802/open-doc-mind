interface StatusBarProps {
  scope: 'all' | string;
  onClear: () => void;
  onToggleScope: (docId: string | null) => void;
  documents: { id: string; file_name: string }[];
}

export function StatusBar({ scope, onClear, onToggleScope, documents }: StatusBarProps) {
  const scopeLabel = scope === 'all' ? 'all documents' : scope;

  return (
    <header className="h-14 bg-ink text-parchment flex items-center justify-between px-6 border-b border-ink-light">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-xl font-semibold tracking-wide">RAG</h1>
        <span className="text-parchment-dark/50 text-sm">|</span>
        <div className="flex items-center gap-2">
          <span className="text-sm text-parchment-dark/70">Searching:</span>
          <div className="relative group">
            <button className="text-sm font-medium text-gold hover:text-gold-light transition-colors flex items-center gap-1">
              {scopeLabel}
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <div className="absolute top-full left-0 mt-1 bg-ink-light border border-ink rounded shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 min-w-48">
              <button
                onClick={() => onToggleScope(null)}
                className={`block w-full text-left px-4 py-2 text-sm hover:bg-ink transition-colors ${scope === 'all' ? 'text-gold' : 'text-parchment'}`}
              >
                All documents
              </button>
              {documents.map(doc => (
                <button
                  key={doc.id}
                  onClick={() => onToggleScope(doc.id)}
                  className={`block w-full text-left px-4 py-2 text-sm hover:bg-ink transition-colors truncate ${scope === doc.file_name ? 'text-gold' : 'text-parchment'}`}
                >
                  {doc.file_name}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
      <button
        onClick={onClear}
        className="text-sm text-parchment-dark/70 hover:text-parchment transition-colors"
      >
        Clear chat
      </button>
    </header>
  );
}