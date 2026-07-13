import { apiRequest } from "./client";
import type { UserProfile } from "./account";
import type { Escalation, EscalationContact } from "./intelligence";

export type KnowledgeDocument = {
  id: string;
  title: string;
  source_type: string;
  source_uri: string | null;
  content_type: string;
  language: string;
  status: string;
  current_version: number;
  checksum: string;
  duplicate_of_document_id: string | null;
  ingested_by_user_id: string | null;
  document_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type KnowledgeDryRunDocument = {
  source_uri: string;
  title: string;
  content_type: string;
  parser: string;
  language: string;
  word_count: number;
  chunk_count: number;
  checksum: string;
  existing_document_id: string | null;
  duplicate_document_id: string | null;
  would_create_document: boolean;
  would_reindex: boolean;
  would_skip_unchanged: boolean;
  embedding_configured: boolean;
};

export type KnowledgeIngestResponse = {
  documents: KnowledgeDocument[];
  ingested_count: number;
  skipped_count: number;
  errors: string[];
  dry_run: boolean;
  dry_run_documents: KnowledgeDryRunDocument[];
};

export type IntelligenceSource = {
  id: string;
  name: string;
  source_type: string;
  source_format: string;
  url: string;
  language: string;
  country: string | null;
  state: string | null;
  district: string | null;
  crop_tags: string[];
  credibility_score: string;
  is_active: boolean;
  last_synced_at: string | null;
  source_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type HealthReport = Record<string, unknown>;

type JsonSafe =
  | string
  | number
  | boolean
  | null
  | JsonSafe[]
  | { [key: string]: JsonSafe };

export type EscalationContactInput = {
  name: string;
  contact_type: string;
  role?: string | null;
  organization?: string | null;
  district?: string | null;
  state?: string | null;
  phone_number?: string | null;
  email?: string | null;
  preferred_channel?: string;
  is_active?: boolean;
  contact_priority?: number;
  is_fallback?: boolean;
  notes?: string | null;
  service_area?: Record<string, JsonSafe>;
};

export async function listAdminUsers(authToken: string) {
  return apiRequest<UserProfile[]>("/users/admin/users?limit=100&skip=0", {
    method: "GET",
    authToken,
  });
}

export async function listAdminKnowledgeDocuments(authToken: string) {
  return apiRequest<KnowledgeDocument[]>("/admin/knowledge/documents?limit=100&skip=0", {
    method: "GET",
    authToken,
  });
}

export async function uploadKnowledgeDocument(
  authToken: string,
  payload: {
    file: File;
    title: string;
    sourceUri: string;
    language: string;
    metadata: Record<string, unknown>;
    dryRun: boolean;
    forceReindex: boolean;
  },
) {
  const formData = new FormData();
  formData.set("file", payload.file);
  formData.set("title", payload.title);
  formData.set("source_uri", payload.sourceUri);
  formData.set("language", payload.language);
  formData.set("metadata_json", JSON.stringify(payload.metadata));
  formData.set("dry_run", String(payload.dryRun));
  formData.set("force_reindex", String(payload.forceReindex));

  return apiRequest<KnowledgeIngestResponse>("/admin/knowledge/documents", {
    method: "POST",
    authToken,
    body: formData,
    timeoutMs: 60000,
  });
}

export async function reindexKnowledgeDocument(authToken: string, documentId: string) {
  return apiRequest<KnowledgeDocument>(
    `/admin/knowledge/documents/${documentId}/reindex`,
    {
      method: "POST",
      authToken,
      timeoutMs: 60000,
    },
  );
}

export async function softDeleteKnowledgeDocument(authToken: string, documentId: string) {
  return apiRequest<KnowledgeDocument>(`/admin/knowledge/documents/${documentId}`, {
    method: "DELETE",
    authToken,
  });
}

export async function listAdminEscalationContacts(authToken: string) {
  return apiRequest<EscalationContact[]>("/admin/escalation-contacts?limit=100&skip=0", {
    method: "GET",
    authToken,
  });
}

export async function createAdminEscalationContact(
  authToken: string,
  payload: EscalationContactInput,
) {
  return apiRequest<EscalationContact>("/admin/escalation-contacts", {
    method: "POST",
    authToken,
    body: payload,
  });
}

export async function updateAdminEscalationContact(
  authToken: string,
  contactId: string,
  payload: EscalationContactInput,
) {
  return apiRequest<EscalationContact>(`/admin/escalation-contacts/${contactId}`, {
    method: "PUT",
    authToken,
    body: payload,
  });
}

export async function listAdminEscalations(authToken: string) {
  return apiRequest<Escalation[]>("/admin/escalations?limit=100&skip=0", {
    method: "GET",
    authToken,
  });
}

export async function listIntelligenceSources(authToken: string) {
  return apiRequest<IntelligenceSource[]>("/admin/intelligence/sources?limit=100&skip=0", {
    method: "GET",
    authToken,
  });
}

export async function syncIntelligenceSources(authToken: string, dryRun = true) {
  return apiRequest<Record<string, unknown>>(
    `/admin/intelligence/sources/sync?dry_run=${String(dryRun)}`,
    {
      method: "POST",
      authToken,
      timeoutMs: 60000,
    },
  );
}

export async function getSystemHealth(authToken: string) {
  return apiRequest<HealthReport>("/health", {
    method: "GET",
    authToken,
  });
}

export async function getProviderHealth(authToken: string) {
  const [rag, embeddings, health] = await Promise.allSettled([
    apiRequest<HealthReport>("/health/rag", { method: "GET", authToken }),
    apiRequest<HealthReport>("/health/embeddings", { method: "GET", authToken }),
    apiRequest<HealthReport>("/health", { method: "GET", authToken }),
  ]);

  return { rag, embeddings, health };
}
