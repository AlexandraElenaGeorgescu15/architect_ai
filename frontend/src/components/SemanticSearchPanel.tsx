import { useState } from 'react'
import { Search, Link as LinkIcon, Clipboard } from 'lucide-react'
import { SemanticSearchResult, semanticSearch } from '../services/codeSearchService'
import { useUIStore } from '../stores/uiStore'

interface SemanticSearchPanelProps {
  onInsertSnippet?: (content: string) => void
}

export default function SemanticSearchPanel({ onInsertSnippet }: SemanticSearchPanelProps) {
  const [query, setQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [results, setResults] = useState<SemanticSearchResult[]>([])
  const { addNotification } = useUIStore()

  const handleSearch = async () => {
    if (!query.trim()) {
      return
    }

    setIsSearching(true)
    try {
      const response = await semanticSearch({ query, limit: 20 })
      setResults(response.results)
    } catch (error) {
      // Semantic search failed - show notification
      addNotification('error', 'Semantic search failed. Please try again.')
    } finally {
      setIsSearching(false)
    }
  }

  const handleInsert = (snippet: string) => {
    if (onInsertSnippet) {
      onInsertSnippet(snippet)
      addNotification('success', 'Snippet added to meeting notes.')
    } else {
      navigator.clipboard
        .writeText(snippet)
        .then(() => addNotification('success', 'Snippet copied to clipboard.'))
        .catch(() => addNotification('error', 'Failed to copy snippet.'))
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search codebase (e.g. payment service, auth middleware)"
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary focus:outline-none"
          />
        </div>
        <button
          onClick={handleSearch}
          disabled={isSearching || query.trim().length < 2}
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
        >
          {isSearching ? 'Searching...' : 'Search'}
        </button>
      </div>

      <div className="space-y-2 max-h-72 overflow-y-auto pr-1 custom-scrollbar">
        {results.length === 0 && !isSearching && (
          <p className="text-sm text-muted-foreground text-center py-6">
            Search your repository to pull relevant snippets into the context.
          </p>
        )}

        {results.map((result, idx) => (
          <div key={`${result.file_path}-${idx}`} className="border border-border rounded-lg p-3 space-y-2 bg-card/80">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="truncate" title={result.file_path}>
                {result.file_path}
                {result.start_line !== undefined && (
                  <> · L{result.start_line}{result.end_line ? `-${result.end_line}` : ''}</>
                )}
              </span>
              <span>{(result.score * 100).toFixed(1)}%</span>
            </div>
            <pre className="text-xs bg-muted p-2 rounded-md max-h-32 overflow-y-auto whitespace-pre-wrap">
              {result.content.trim()}
            </pre>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleInsert(result.content)}
                className="px-2 py-1 text-xs border border-border rounded-md hover:bg-primary/10 flex items-center gap-1"
              >
                <Clipboard className="w-3 h-3" />
                {onInsertSnippet ? 'Insert into notes' : 'Copy'}
              </button>
              <a
                href={result.metadata?.url as string | undefined}
                target="_blank"
                rel="noreferrer"
                className="px-2 py-1 text-xs border border-border rounded-md hover:bg-muted flex items-center gap-1"
              >
                <LinkIcon className="w-3 h-3" />
                Open
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

