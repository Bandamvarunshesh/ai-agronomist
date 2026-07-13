import { useEffect, useState, type FormEvent } from "react";

import { useAuth } from "../../auth/auth-store";
import { EmptyState, InlineAlert, PageSkeleton, PermissionDeniedState } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";
import {
  listAdminKnowledgeDocuments,
  reindexKnowledgeDocument,
  softDeleteKnowledgeDocument,
  uploadKnowledgeDocument,
  type KnowledgeDocument,
  type KnowledgeIngestResponse,
} from "../../lib/api/admin";
import { searchKnowledge, type KnowledgeSearchResponse } from "../../lib/api/intelligence";

const trustedSources = ["ICAR", "IARI", "KVK", "agricultural universities", "government agriculture departments", "FAO"];

export function AdminKnowledgePage() {
  const { state } = useAuth();
  const { pushToast } = useToast();
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<KnowledgeIngestResponse | null>(null);
  const [searchResult, setSearchResult] = useState<KnowledgeSearchResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [form, setForm] = useState({
    title: "",
    sourceUri: "",
    language: "en",
    sourceOrganization: "",
    cropTags: "",
    stateRegionTags: "",
    documentVersion: "",
    dryRun: true,
    forceReindex: false,
  });
  const [file, setFile] = useState<File | null>(null);

  const loadDocuments = async () => {
    if (!state.token) return;
    setStatus("loading");
    try {
      setDocuments(await listAdminKnowledgeDocuments(state.token));
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  };

  useEffect(() => {
    if (state.user?.role === "admin") {
      void loadDocuments();
    }
  }, [state.token, state.user?.role]);

  if (state.user?.role !== "admin") {
    return <PermissionDeniedState message="Knowledge management requires an admin account." />;
  }

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!state.token || !file) return;
    setUploading(true);
    try {
      const response = await uploadKnowledgeDocument(state.token, {
        file,
        title: form.title,
        sourceUri: form.sourceUri || file.name,
        language: form.language,
        dryRun: form.dryRun,
        forceReindex: form.forceReindex,
        metadata: {
          source_organization: form.sourceOrganization,
          crop_tags: form.cropTags.split(",").map((tag) => tag.trim()).filter(Boolean),
          state_region_tags: form.stateRegionTags.split(",").map((tag) => tag.trim()).filter(Boolean),
          document_version: form.documentVersion,
        },
      });
      setUploadResult(response);
      pushToast({ title: form.dryRun ? "Dry run complete" : "Document uploaded", message: "Knowledge ingestion completed.", tone: "success" });
      if (!form.dryRun) {
        await loadDocuments();
      }
    } catch {
      pushToast({ title: "Upload unavailable", message: "Unable to process the document right now.", tone: "error" });
    } finally {
      setUploading(false);
    }
  };

  const handleSearch = async () => {
    if (!state.token || !searchQuery.trim()) return;
    try {
      setSearchResult(await searchKnowledge(state.token, { query: searchQuery, limit: 5 }));
    } catch {
      pushToast({ title: "Search unavailable", message: "Semantic search verification could not run.", tone: "error" });
    }
  };

  const mutateDocument = async (action: "reindex" | "delete", documentId: string) => {
    if (!state.token) return;
    try {
      await (action === "reindex"
        ? reindexKnowledgeDocument(state.token, documentId)
        : softDeleteKnowledgeDocument(state.token, documentId));
      pushToast({ title: action === "reindex" ? "Re-index queued" : "Document deleted", message: "Knowledge document status was updated.", tone: "success" });
      await loadDocuments();
    } catch {
      pushToast({ title: "Action failed", message: "Unable to update the knowledge document.", tone: "error" });
    }
  };

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div><div className="eyebrow">Management</div><h2 className="surface-title">Knowledge documents</h2><p className="surface-copy">Upload trusted agricultural sources, validate parsing, and verify retrieval quality.</p></div>
      </article>

      <form className="surface-card form-stack" onSubmit={handleUpload}>
        <h3 className="section-title">Upload or dry-run validation</h3>
        <div className="form-grid">
          <label className="field field-span-full"><span className="field-label">Document</span><input className="input" accept=".pdf,.docx,.txt,.md,.markdown,.html,.htm,application/pdf,text/plain,text/markdown,text/html,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => setFile(event.target.files?.[0] || null)} type="file" /></label>
          <label className="field"><span className="field-label">Title</span><input className="input" value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} /></label>
          <label className="field"><span className="field-label">Source URI</span><input className="input" value={form.sourceUri} onChange={(event) => setForm((current) => ({ ...current, sourceUri: event.target.value }))} /></label>
          <label className="field"><span className="field-label">Source organization</span><input className="input" value={form.sourceOrganization} onChange={(event) => setForm((current) => ({ ...current, sourceOrganization: event.target.value }))} /></label>
          <label className="field"><span className="field-label">Language</span><input className="input" value={form.language} onChange={(event) => setForm((current) => ({ ...current, language: event.target.value }))} /></label>
          <label className="field"><span className="field-label">Crop tags</span><input className="input" value={form.cropTags} onChange={(event) => setForm((current) => ({ ...current, cropTags: event.target.value }))} /></label>
          <label className="field"><span className="field-label">State/region tags</span><input className="input" value={form.stateRegionTags} onChange={(event) => setForm((current) => ({ ...current, stateRegionTags: event.target.value }))} /></label>
          <label className="field"><span className="field-label">Document version</span><input className="input" value={form.documentVersion} onChange={(event) => setForm((current) => ({ ...current, documentVersion: event.target.value }))} /></label>
          <label className="checkbox-row align-end"><input checked={form.dryRun} onChange={(event) => setForm((current) => ({ ...current, dryRun: event.target.checked }))} type="checkbox" /><span>Dry-run validation</span></label>
          <label className="checkbox-row align-end"><input checked={form.forceReindex} onChange={(event) => setForm((current) => ({ ...current, forceReindex: event.target.checked }))} type="checkbox" /><span>Force re-index</span></label>
        </div>
        <div className="button-row"><button className="button button-primary" disabled={!file || uploading} type="submit">{uploading ? "Processing..." : form.dryRun ? "Validate document" : "Upload document"}</button></div>
      </form>

      {uploadResult ? (
        <InlineAlert
          title={uploadResult.dry_run ? "Dry-run result" : "Ingestion result"}
          message={`${uploadResult.ingested_count} ingested, ${uploadResult.skipped_count} skipped, ${uploadResult.errors.length} errors.`}
          tone={uploadResult.errors.length ? "warning" : "info"}
        />
      ) : null}

      <article className="surface-card form-stack">
        <h3 className="section-title">Semantic-search verification</h3>
        <div className="button-row">
          <input className="input" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Verify that trusted sources answer a crop question" />
          <button className="button button-secondary" disabled={!searchQuery.trim()} onClick={() => void handleSearch()} type="button">Run search</button>
        </div>
        {searchResult ? <p className="surface-copy">{searchResult.results.length} results returned for "{searchResult.query}".</p> : null}
      </article>

      {status === "loading" ? <PageSkeleton title="Loading documents" /> : null}
      {status === "error" ? <InlineAlert title="Documents unavailable" message="Unable to load knowledge documents." action={<button className="button button-primary" onClick={() => void loadDocuments()} type="button">Retry</button>} /> : null}
      {status === "ready" && !documents.length ? (
        <EmptyState
          title="No trusted knowledge documents uploaded yet."
          message={`Upload trusted sources such as ${trustedSources.join(", ")}.`}
        />
      ) : null}
      {documents.length ? (
        <article className="surface-card">
          <div className="list-stack">
            {documents.map((document) => (
              <div className="list-item list-item-block" key={document.id}>
                <div className="list-row"><div className="list-title">{document.title}</div><div className="pill">{document.status}</div></div>
                <div className="list-meta">{document.content_type} | {document.language} | v{document.current_version}</div>
                <p className="list-body">{document.source_uri || "No source URI"}</p>
                <div className="button-row">
                  <button className="button button-secondary" onClick={() => void mutateDocument("reindex", document.id)} type="button">Re-index</button>
                  <button className="button button-danger" onClick={() => void mutateDocument("delete", document.id)} type="button">Soft delete</button>
                </div>
              </div>
            ))}
          </div>
        </article>
      ) : null}
    </section>
  );
}
