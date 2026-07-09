import { apiRequest } from "./client";

export type ChatCitation = {
  document_id: string;
  version_id: string;
  chunk_id: string;
  title: string;
  source_uri: string | null;
  citation_label: string;
};

export type ChatSession = {
  id: string;
  user_id: string;
  farm_id: string | null;
  title: string | null;
  channel: string;
  status: string;
  session_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  session_id: string;
  user_id: string | null;
  role: string;
  content: string;
  message_metadata: Record<string, unknown>;
  sent_at: string;
  created_at: string;
  updated_at: string;
};

export type ChatMessageExchange = {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
};

export type StoredChatSession = ChatSession;

const CHAT_SESSION_STORAGE_KEY = "ai-agronomist.chat-sessions";

export async function createChatSession(
  authToken: string,
  payload: {
    farm_id?: string | null;
    title?: string | null;
    channel?: string;
  },
) {
  return apiRequest<ChatSession>("/chat/sessions", {
    method: "POST",
    authToken,
    body: payload,
  });
}

export async function sendChatMessage(
  authToken: string,
  sessionId: string,
  payload: { content: string },
) {
  return apiRequest<ChatMessageExchange>(`/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    authToken,
    body: payload,
  });
}

export async function listChatMessages(
  authToken: string,
  sessionId: string,
  options: { skip?: number; limit?: number } = {},
) {
  const params = new URLSearchParams({
    skip: String(options.skip ?? 0),
    limit: String(options.limit ?? 100),
  });

  return apiRequest<ChatMessage[]>(
    `/chat/sessions/${sessionId}/messages?${params.toString()}`,
    {
      method: "GET",
      authToken,
    },
  );
}

export function deriveChatSessionTitle(content: string) {
  const title = content.trim().replace(/\s+/g, " ");
  if (!title) {
    return "Farming chat";
  }
  if (title.length > 80) {
    return `${title.slice(0, 77).trimEnd()}...`;
  }
  return title;
}

function readStoredChatSessions() {
  const raw = window.localStorage.getItem(CHAT_SESSION_STORAGE_KEY);
  if (!raw) {
    return [] as StoredChatSession[];
  }

  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as StoredChatSession[]) : [];
  } catch {
    return [];
  }
}

function writeStoredChatSessions(sessions: StoredChatSession[]) {
  window.localStorage.setItem(CHAT_SESSION_STORAGE_KEY, JSON.stringify(sessions));
}

export function listStoredChatSessionsForUser(userId: string) {
  return readStoredChatSessions()
    .filter((session) => session.user_id === userId)
    .sort(
      (left, right) =>
        new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
    );
}

export function upsertStoredChatSession(session: StoredChatSession) {
  const sessions = readStoredChatSessions();
  const nextSessions = [
    session,
    ...sessions.filter(
      (storedSession) =>
        !(
          storedSession.id === session.id &&
          storedSession.user_id === session.user_id
        ),
    ),
  ];
  writeStoredChatSessions(nextSessions);
}

export function updateStoredChatSession(
  userId: string,
  sessionId: string,
  updates: Partial<StoredChatSession>,
) {
  const sessions = readStoredChatSessions();
  const nextSessions = sessions.map((session) => {
    if (session.user_id !== userId || session.id !== sessionId) {
      return session;
    }
    return { ...session, ...updates };
  });
  writeStoredChatSessions(nextSessions);
}
