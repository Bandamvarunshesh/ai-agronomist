import { useEffect, useMemo, useRef, useState, type KeyboardEventHandler } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { MarkdownMessage } from "../../components/chat/MarkdownMessage";
import { InlineAlert } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";
import { ApiError } from "../../lib/api/client";
import {
  createChatSession,
  deriveChatSessionTitle,
  listChatMessages,
  listStoredChatSessionsForUser,
  sendChatMessage,
  updateStoredChatSession,
  upsertStoredChatSession,
  type ChatCitation,
  type ChatMessage,
  type ChatSession,
} from "../../lib/api/chat";
import { listFarms, type Farm } from "../../lib/api/farms";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatRelativeTime(value: string) {
  const deltaMinutes = Math.round((new Date(value).getTime() - Date.now()) / 60000);

  if (Math.abs(deltaMinutes) < 60) {
    return new Intl.RelativeTimeFormat(undefined, { numeric: "auto" }).format(
      deltaMinutes,
      "minute",
    );
  }

  const deltaHours = Math.round(deltaMinutes / 60);
  if (Math.abs(deltaHours) < 24) {
    return new Intl.RelativeTimeFormat(undefined, { numeric: "auto" }).format(
      deltaHours,
      "hour",
    );
  }

  const deltaDays = Math.round(deltaHours / 24);
  return new Intl.RelativeTimeFormat(undefined, { numeric: "auto" }).format(
    deltaDays,
    "day",
  );
}

function getMessageCitations(message: ChatMessage): ChatCitation[] {
  const citations = message.message_metadata?.citations;
  return Array.isArray(citations) ? (citations as ChatCitation[]) : [];
}

const SOURCE_REQUEST_PATTERN =
  /\b(source|sources|reference|references|document|documents|citation|citations|cite|cited|docs)\b/i;

function userExplicitlyAskedForSources(content: string) {
  return SOURCE_REQUEST_PATTERN.test(content);
}

function shouldAutoExpandSources(messages: ChatMessage[], assistantIndex: number) {
  for (let index = assistantIndex - 1; index >= 0; index -= 1) {
    const candidate = messages[index];
    if (candidate.role !== "user") {
      continue;
    }
    return userExplicitlyAskedForSources(candidate.content);
  }

  return false;
}

export function ChatPage() {
  const { state } = useAuth();
  const { pushToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messagesStatus, setMessagesStatus] = useState<"idle" | "loading" | "ready" | "error">(
    "idle",
  );
  const [messageError, setMessageError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [creatingSession, setCreatingSession] = useState(false);
  const [sending, setSending] = useState(false);
  const [sessionRegistryTick, setSessionRegistryTick] = useState(0);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const sessionId = searchParams.get("sessionId") || "";
  const selectedFarmId = searchParams.get("farmId") || "";
  const userId = state.user?.id || "";

  const storedSessions = useMemo(
    () => (userId ? listStoredChatSessionsForUser(userId) : []),
    [sessionRegistryTick, userId],
  );

  const farmsById = useMemo(
    () =>
      farms.reduce<Record<string, Farm>>((accumulator, farm) => {
        accumulator[farm.id] = farm;
        return accumulator;
      }, {}),
    [farms],
  );

  const filteredSessions = useMemo(() => {
    if (!selectedFarmId) {
      return storedSessions;
    }
    return storedSessions.filter((session) => session.farm_id === selectedFarmId);
  }, [selectedFarmId, storedSessions]);

  const activeSession = useMemo(
    () => storedSessions.find((session) => session.id === sessionId) || null,
    [sessionId, storedSessions],
  );

  useEffect(() => {
    if (state.status !== "authenticated" || !state.token) {
      return;
    }

    let cancelled = false;

    const loadContext = async () => {
      setStatus("loading");
      setError(null);

      try {
        const farmsResponse = await listFarms(state.token!);
        if (cancelled) {
          return;
        }
        setFarms(farmsResponse);
        setStatus("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load chat context right now.",
        );
        setStatus("error");
      }
    };

    void loadContext();

    return () => {
      cancelled = true;
    };
  }, [state.status, state.token]);

  useEffect(() => {
    if (sessionId || !filteredSessions.length) {
      return;
    }

    const nextSession = filteredSessions[0];
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("sessionId", nextSession.id);
    if (nextSession.farm_id) {
      nextParams.set("farmId", nextSession.farm_id);
    } else {
      nextParams.delete("farmId");
    }
    setSearchParams(nextParams, { replace: true });
  }, [filteredSessions, searchParams, sessionId, setSearchParams]);

  useEffect(() => {
    if (state.status !== "authenticated" || !state.token || !sessionId) {
      setMessages([]);
      setMessagesStatus("idle");
      setMessageError(null);
      return;
    }

    let cancelled = false;

    const loadMessages = async () => {
      setMessagesStatus("loading");
      setMessageError(null);

      try {
        const response = await listChatMessages(state.token!, sessionId);
        if (cancelled) {
          return;
        }
        setMessages(response);
        setMessagesStatus("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }

        if (loadError instanceof ApiError && loadError.status === 404) {
          setMessageError("This chat session could not be found.");
        } else {
          setMessageError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load chat messages right now.",
          );
        }
        setMessagesStatus("error");
      }
    };

    void loadMessages();

    return () => {
      cancelled = true;
    };
  }, [sessionId, state.status, state.token]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  useEffect(() => {
    setExpandedSources((current) => {
      let changed = false;
      const nextState = { ...current };

      messages.forEach((message, index) => {
        if (message.role !== "assistant" || !getMessageCitations(message).length) {
          return;
        }
        if (!shouldAutoExpandSources(messages, index) || nextState[message.id]) {
          return;
        }

        nextState[message.id] = true;
        changed = true;
      });

      return changed ? nextState : current;
    });
  }, [messages]);

  const setFarmFilter = (farmId: string) => {
    const nextParams = new URLSearchParams(searchParams);
    if (farmId) {
      nextParams.set("farmId", farmId);
    } else {
      nextParams.delete("farmId");
    }

    if (activeSession && activeSession.farm_id !== (farmId || null)) {
      nextParams.delete("sessionId");
    }

    setSearchParams(nextParams);
  };

  const selectSession = (session: ChatSession) => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("sessionId", session.id);
    if (session.farm_id) {
      nextParams.set("farmId", session.farm_id);
    } else {
      nextParams.delete("farmId");
    }
    setSearchParams(nextParams);
  };

  const handleCreateSession = async () => {
    if (!state.token) {
      return null;
    }

    setCreatingSession(true);
    setError(null);

    try {
      const session = await createChatSession(state.token, {
        farm_id: selectedFarmId || null,
        channel: "web",
      });
      upsertStoredChatSession(session);
      setSessionRegistryTick((current) => current + 1);
      selectSession(session);
      setMessages([]);
      setMessagesStatus("ready");
      pushToast({
        title: "Chat session created",
        message: selectedFarmId
          ? "The new session is linked to the selected farm."
          : "The new session is ready.",
        tone: "success",
      });
      return session;
    } catch (createError) {
      const detail =
        createError instanceof Error
          ? createError.message
          : "Unable to create a chat session right now.";
      setError(detail);
      pushToast({
        title: "Session creation failed",
        message: detail,
        tone: "error",
      });
      return null;
    } finally {
      setCreatingSession(false);
    }
  };

  const handleSend = async () => {
    const content = draft.trim();
    if (!state.token || !content || sending) {
      return;
    }

    setSending(true);
    setMessageError(null);

    let nextSession = activeSession;
    if (!nextSession) {
      nextSession = await handleCreateSession();
      if (!nextSession) {
        setSending(false);
        return;
      }
    }

    const nextDraft = content;
    setDraft("");

    try {
      const exchange = await sendChatMessage(state.token, nextSession.id, {
        content: nextDraft,
      });
      setMessages((current) => [
        ...current,
        exchange.user_message,
        exchange.assistant_message,
      ]);
      setMessagesStatus("ready");

      const nextTitle =
        nextSession.title || deriveChatSessionTitle(exchange.user_message.content);
      updateStoredChatSession(userId, nextSession.id, {
        title: nextTitle,
        updated_at: exchange.assistant_message.updated_at,
      });
      setSessionRegistryTick((current) => current + 1);
      pushToast({
        title: "Reply received",
        message: "The farming assistant has responded.",
        tone: "success",
      });
    } catch (sendError) {
      setDraft(nextDraft);
      const detail =
        sendError instanceof Error
          ? sendError.message
          : "Unable to send the message right now.";
      setMessageError(detail);
      pushToast({
        title: "Message failed",
        message: detail,
        tone: "error",
      });
    } finally {
      setSending(false);
    }
  };

  const handleComposerKeyDown: KeyboardEventHandler<HTMLTextAreaElement> = (
    event,
  ) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  };

  const toggleSources = (messageId: string) => {
    setExpandedSources((current) => ({
      ...current,
      [messageId]: !current[messageId],
    }));
  };

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">AI farming chat</div>
          <h2 className="surface-title">Farming assistant</h2>
          <p className="surface-copy">
            Start farm-linked or general farming conversations using the existing chat
            APIs and Gemini-backed assistant responses.
          </p>
        </div>
        <div className="button-row">
          <div className="field-inline">
            <label className="field-label" htmlFor="chat-farm-filter">
              Linked farm
            </label>
            <select
              className="input select-input"
              id="chat-farm-filter"
              onChange={(event) => setFarmFilter(event.target.value)}
              value={selectedFarmId}
            >
              <option value="">General farming chat</option>
              {farms.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.farm_name}
                </option>
              ))}
            </select>
          </div>
          <button
            className="button button-primary"
            disabled={creatingSession || status !== "ready"}
            onClick={() => void handleCreateSession()}
            type="button"
          >
            {creatingSession ? "Creating..." : "New session"}
          </button>
        </div>
      </article>

      {status === "error" ? (
        <InlineAlert
          title="Chat unavailable"
          message={error || "Unable to load the chat workspace right now."}
        />
      ) : null}

      <div className="chat-layout">
        <aside className="surface-card chat-sidebar">
          <div className="panel-header">
            <div>
              <h3 className="section-title">Sessions</h3>
              <p className="surface-copy">
                Sessions are created on the backend and remembered in this browser.
              </p>
            </div>
          </div>

          {filteredSessions.length ? (
            <div className="chat-session-list">
              {filteredSessions.map((session) => {
                const farm = session.farm_id ? farmsById[session.farm_id] : null;
                const isActive = session.id === sessionId;
                return (
                  <button
                    className={
                      isActive ? "chat-session-card chat-session-card-active" : "chat-session-card"
                    }
                    key={session.id}
                    onClick={() => selectSession(session)}
                    type="button"
                  >
                    <div className="list-title">
                      {session.title || "Untitled farming chat"}
                    </div>
                    <div className="list-meta">
                      {farm ? farm.farm_name : "General farming chat"}
                    </div>
                    <div className="list-meta">{formatRelativeTime(session.updated_at)}</div>
                  </button>
                );
              })}
            </div>
          ) : (
            <InlineAlert
              title="No known sessions"
              message="Create a new session to begin chatting. Until the backend exposes session listing, only sessions created in this browser appear here."
              tone="info"
            />
          )}
        </aside>

        <section className="surface-card chat-panel">
          <div className="chat-panel-header">
            <div>
              <h3 className="section-title">
                {activeSession?.title ||
                  (selectedFarmId
                    ? `${farmsById[selectedFarmId]?.farm_name || "Farm"} chat`
                    : "New farming chat")}
              </h3>
              <p className="surface-copy">
                {activeSession?.farm_id
                  ? `Linked to ${farmsById[activeSession.farm_id]?.farm_name || "selected farm"}`
                  : selectedFarmId
                    ? `Ready to link the next session to ${farmsById[selectedFarmId]?.farm_name || "the selected farm"}`
                    : "General farming guidance without a linked farm profile"}
              </p>
            </div>
            {activeSession?.farm_id ? (
              <Link
                className="button button-ghost button-link"
                to={`/app/farms/${activeSession.farm_id}`}
              >
                View farm
              </Link>
            ) : null}
          </div>

          {messageError ? (
            <InlineAlert
              title="Messages unavailable"
              message={messageError}
            />
          ) : null}

          <div className="chat-message-region">
            {messagesStatus === "loading" ? (
              <div className="chat-message-list">
                {Array.from({ length: 4 }).map((_, index) => (
                  <div
                    className={
                      index % 2 === 0 ? "chat-bubble chat-bubble-user" : "chat-bubble"
                    }
                    key={index}
                  >
                    <div className="list-meta">Loading conversation...</div>
                  </div>
                ))}
              </div>
            ) : messages.length ? (
              <div className="chat-message-list">
                {messages.map((message, index) => {
                  const citations = getMessageCitations(message);
                  const isUser = message.role === "user";
                  const autoExpandSources =
                    !isUser && citations.length
                      ? shouldAutoExpandSources(messages, index)
                      : false;
                  const sourcesExpanded =
                    !isUser && citations.length
                      ? expandedSources[message.id] ?? autoExpandSources
                      : false;

                  return (
                    <article
                      className={isUser ? "chat-bubble chat-bubble-user" : "chat-bubble"}
                      key={message.id}
                    >
                      <div className="chat-bubble-meta">
                        <span>{isUser ? "You" : "AI Farming Assistant"}</span>
                        <span>{formatDate(message.sent_at)}</span>
                      </div>
                      <MarkdownMessage content={message.content} />
                      {!isUser && citations.length ? (
                        <div className="source-disclosure">
                          <button
                            aria-expanded={sourcesExpanded}
                            className="source-disclosure-toggle"
                            onClick={() => toggleSources(message.id)}
                            type="button"
                          >
                            View Sources
                            <span className="source-disclosure-count">
                              {citations.length}
                            </span>
                          </button>
                          {sourcesExpanded ? (
                            <div className="citation-stack">
                              {citations.map((citation) => (
                                <div className="citation-row" key={citation.chunk_id}>
                                  <div className="list-title">{citation.citation_label}</div>
                                  <div className="list-meta">
                                    {citation.source_uri || citation.title}
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                    </article>
                  );
                })}
                {sending ? (
                  <article className="chat-bubble">
                    <div className="chat-bubble-meta">
                      <span>AI Farming Assistant</span>
                      <span>Thinking...</span>
                    </div>
                    <div className="chat-typing">Generating a response...</div>
                  </article>
                ) : null}
                <div ref={messagesEndRef} />
              </div>
            ) : (
              <div className="chat-empty-state">
                <div className="eyebrow">Ready</div>
                <h3 className="surface-title">Ask about crops, soil, pests, weather decisions, or farm planning.</h3>
                <p className="surface-copy">
                  The first message will start a session automatically if you have not created one yet.
                </p>
              </div>
            )}
          </div>

          <div className="chat-composer">
            <textarea
              className="input chat-textarea"
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder="Ask a farming question..."
              rows={5}
              value={draft}
            />
            <div className="button-row">
              <div className="list-meta">
                {activeSession
                  ? `Session updated ${formatRelativeTime(activeSession.updated_at)}`
                  : "No session yet. Sending will start one."}
              </div>
              <button
                className="button button-primary"
                disabled={!draft.trim() || sending || status !== "ready"}
                onClick={() => void handleSend()}
                type="button"
              >
                {sending ? "Sending..." : "Send message"}
              </button>
            </div>
          </div>
        </section>
      </div>
    </section>
  );
}
