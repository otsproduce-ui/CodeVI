import { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { ArrowLeft, FileCode, ExternalLink, GitGraph, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { search, SearchResult } from "@/lib/api";

export default function Results() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q") || "";
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (query) {
      performSearch(query);
    } else {
      setLoading(false);
    }
  }, [query]);

  async function performSearch(query: string) {
    setLoading(true);
    setError(null);
    try {
      const searchResults = await search(query, 20);
      setResults(searchResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred while searching");
      console.error("Search error:", err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Background effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 right-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-3xl" />
      </div>

      <main className="relative z-10 container px-4 md:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/" className="gap-2">
                <ArrowLeft className="h-4 w-4" />
                <span className="hidden sm:inline">New Search</span>
              </Link>
            </Button>
            <div>
              <p className="text-sm text-muted-foreground">Results for</p>
              <h1 className="text-xl font-semibold text-foreground">{query}</h1>
            </div>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link to="/graph" className="gap-2">
              <GitGraph className="h-4 w-4" />
              <span className="hidden sm:inline">View Graph</span>
            </Link>
          </Button>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-destructive/10 flex items-center justify-center mx-auto mb-4">
              <FileCode className="h-8 w-8 text-destructive" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">Error</h3>
            <p className="text-muted-foreground mb-6">{error}</p>
            <Button variant="glow" asChild>
              <Link to="/">Go Back</Link>
            </Button>
          </div>
        )}

        {/* Results */}
        {!loading && !error && (
          <div className="max-w-4xl space-y-4">
            {results.map((result, index) => {
              const filePath = result.file_path || result.id;
              const code = result.code || result.content || result.snippet || '';
              const lineNumber = result.start_line || result.line_number || 0;
              const relevance = result.relevance || result.score || 0;
              
              return (
                <div
                  key={result.id || index}
                  className={cn(
                    "group p-6 rounded-2xl border border-border/50 bg-card/30 backdrop-blur-sm",
                    "transition-all duration-300 hover:border-primary/30 hover:bg-card/50",
                    "opacity-0 animate-fade-in-up"
                  )}
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                        <FileCode className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <h3 className="font-medium text-foreground group-hover:text-primary transition-colors">
                          {filePath}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          {lineNumber > 0 && `Line ${lineNumber} • `}
                          {relevance > 0 && `${Math.round(relevance * 100)}% match`}
                        </p>
                      </div>
                    </div>
                    <Button variant="ghost" size="icon" className="opacity-0 group-hover:opacity-100 transition-opacity">
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>

                  {/* Code snippet */}
                  {code && (
                    <div className="rounded-xl bg-background/50 border border-border/30 p-4 overflow-x-auto">
                      <pre className="text-sm font-mono text-muted-foreground whitespace-pre-wrap">
                        <code>{code}</code>
                      </pre>
                    </div>
                  )}

                  {/* Relevance bar */}
                  {relevance > 0 && (
                    <div className="mt-4 flex items-center gap-3">
                      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-primary to-primary/60 rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(relevance * 100, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground">{Math.round(relevance * 100)}%</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && results.length === 0 && (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-muted/50 flex items-center justify-center mx-auto mb-4">
              <FileCode className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">No results found</h3>
            <p className="text-muted-foreground mb-6">Try a different query or scan your codebase first.</p>
            <Button variant="glow" asChild>
              <Link to="/">Go Back</Link>
            </Button>
          </div>
        )}
      </main>
    </div>
  );
}
