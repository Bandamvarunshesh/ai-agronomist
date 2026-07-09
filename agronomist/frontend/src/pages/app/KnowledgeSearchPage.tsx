import { useState } from "react";

import { useAuth } from "../../auth/auth-store";
import { InlineAlert } from "../../components/ui/Feedback";
import { searchKnowledge, type KnowledgeSearchResponse } from "../../lib/api/intelligence";

export function KnowledgeSearchPage() {
  const { state } = useAuth();
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState("");
  const [contentType, setContentType] = useState("");
  const [useHybrid, setUseHybrid] = useState(true);
  const [limit, setLimit] = useState(8);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<KnowledgeSearchResponse | null>(null);

  const handleSearch = async () => {
    if (!state.token || !query.trim()) {
      return;
    }
    setStatus("loading");
    setError(null);

    try {
      const response = await searchKnowledge(state.token, {
        query: query.trim(),
        limit,
        language: language || null,
        content_type: contentType || null,
        use_hybrid: useHybrid,
      });
      setResults(response);
      setStatus("ready");
    } catch (searchError) {
      setError(
        searchError instanceof Error
          ? searchError.message
          : "Unable to search knowledge right now.",
      );
      setStatus("error");
    }
  };

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">Knowledge search</div>
          <h2 className="surface-title">Search the knowledge base</h2>
          <p className="surface-copy">
            Search ingested agricultural documents with citations from the backend retrieval system.
          </p>
        </div>
      </article>

      {error ? <InlineAlert title="Knowledge search unavailable" message={error} /> : null}

      <article className="surface-card">
        <div className="form-grid">
          <label className="field field-span-full">
            <span className="field-label">Query</span>
            <input
              className="input"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search for pest control, irrigation planning, soil nutrition..."
              value={query}
            />
          </label>
          <label className="field">
            <span className="field-label">Language</span>
            <input
              className="input"
              onChange={(event) => setLanguage(event.target.value)}
              placeholder="en"
              value={language}
            />
          </label>
          <label className="field">
            <span className="field-label">Content type</span>
            <input
              className="input"
              onChange={(event) => setContentType(event.target.value)}
              placeholder="application/pdf"
              value={contentType}
            />
          </label>
          <label className="field">
            <span className="field-label">Limit</span>
            <input
              className="input"
              max="20"
              min="1"
              onChange={(event) => setLimit(Number(event.target.value) || 8)}
              type="number"
              value={limit}
            />
          </label>
          <label className="checkbox-row align-end">
            <input
              checked={useHybrid}
              onChange={(event) => setUseHybrid(event.target.checked)}
              type="checkbox"
            />
            <span>Use hybrid retrieval</span>
          </label>
        </div>

        <div className="button-row">
          <div className="list-meta">
            {results ? `${results.results.length} results` : "No search yet"}
          </div>
          <button
            className="button button-primary"
            disabled={!query.trim() || status === "loading"}
            onClick={() => void handleSearch()}
            type="button"
          >
            {status === "loading" ? "Searching..." : "Search knowledge"}
          </button>
        </div>
      </article>

      {results ? (
        <div className="list-stack">
          {results.results.map((result) => (
            <article className="surface-card" key={result.chunk_id}>
              <div className="panel-header">
                <div>
                  <h3 className="section-title">{result.title}</h3>
                  <div className="list-meta">
                    {result.citation.citation_label} | Score {result.score.toFixed(3)} |
                    Semantic {result.semantic_score.toFixed(3)} | Lexical{" "}
                    {result.lexical_score.toFixed(3)}
                  </div>
                </div>
                {results.cache_hit ? <div className="pill">Cache hit</div> : null}
              </div>
              <p className="list-body">{result.content}</p>
              <div className="citation-row">
                <div className="meta-label">Source</div>
                <div className="list-meta">
                  {result.citation.source_uri || result.citation.title}
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : status === "idle" ? (
        <article className="surface-card">
          <div className="eyebrow">Ready</div>
          <h3 className="surface-title">Search across ingested agricultural knowledge.</h3>
          <p className="surface-copy">
            Results will appear here with retrieval scores and citations.
          </p>
        </article>
      ) : null}
    </section>
  );
}
