import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../auth/auth-store";
import { InlineAlert } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";
import {
  getNotificationPreferences,
  listNotifications,
  markNotificationRead,
  updateNotificationPreferences,
  type Notification,
  type NotificationPreference,
} from "../../lib/api/intelligence";

const notificationTypeLabels: Array<{ key: string; label: string }> = [
  { key: "weather_alert", label: "Weather alerts" },
  { key: "irrigation_reminder", label: "Irrigation reminders" },
  { key: "fertilizer_reminder", label: "Fertilizer reminders" },
  { key: "disease_alert", label: "Disease alerts" },
  { key: "crop_stage_reminder", label: "Crop stage reminders" },
  { key: "farming_task_reminder", label: "Task reminders" },
  { key: "daily_ai_summary", label: "Daily AI summary" },
  { key: "weekly_ai_summary", label: "Weekly AI summary" },
  { key: "high_risk_alert", label: "High-risk alerts" },
  { key: "recommendation_generated", label: "Recommendation generated" },
  { key: "farm_health_alert", label: "Farm health alerts" },
];

function formatDate(value: string | null) {
  if (!value) {
    return "Not available";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function NotificationsPage() {
  const { state } = useAuth();
  const { pushToast } = useToast();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [preferences, setPreferences] = useState<NotificationPreference | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [savingPreferences, setSavingPreferences] = useState(false);

  useEffect(() => {
    if (state.status !== "authenticated" || !state.token) {
      return;
    }
    let cancelled = false;

    const loadPage = async () => {
      setStatus("loading");
      setError(null);

      try {
        const [notificationResponse, preferenceResponse] = await Promise.all([
          listNotifications(state.token!, 50),
          getNotificationPreferences(state.token!),
        ]);
        if (cancelled) {
          return;
        }
        setNotifications(notificationResponse);
        setPreferences(preferenceResponse);
        setStatus("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load notifications right now.",
        );
        setStatus("error");
      }
    };

    void loadPage();
    return () => {
      cancelled = true;
    };
  }, [refreshTick, state.status, state.token]);

  const visibleNotifications = useMemo(
    () =>
      unreadOnly
        ? notifications.filter((notification) => !notification.is_read)
        : notifications,
    [notifications, unreadOnly],
  );

  const handleMarkRead = async (notificationId: string) => {
    if (!state.token) {
      return;
    }

    try {
      const updated = await markNotificationRead(state.token, notificationId);
      setNotifications((current) =>
        current.map((notification) =>
          notification.id === updated.id ? updated : notification,
        ),
      );
    } catch (markError) {
      pushToast({
        title: "Unable to mark notification as read",
        message:
          markError instanceof Error
            ? markError.message
            : "Something went wrong.",
        tone: "error",
      });
    }
  };

  const handleSavePreferences = async () => {
    if (!state.token || !preferences) {
      return;
    }
    setSavingPreferences(true);
    setError(null);

    try {
      const updated = await updateNotificationPreferences(state.token, {
        notifications_enabled: preferences.notifications_enabled,
        in_app_enabled: preferences.in_app_enabled,
        push_enabled: preferences.push_enabled,
        email_enabled: preferences.email_enabled,
        sms_enabled: preferences.sms_enabled,
        enabled_types: preferences.enabled_types,
        quiet_hours_enabled: preferences.quiet_hours_enabled,
        quiet_hours_start: preferences.quiet_hours_start,
        quiet_hours_end: preferences.quiet_hours_end,
        timezone: preferences.timezone,
      });
      setPreferences(updated);
      pushToast({
        title: "Preferences saved",
        message: "Notification preferences were updated.",
        tone: "success",
      });
    } catch (saveError) {
      const detail =
        saveError instanceof Error
          ? saveError.message
          : "Unable to save preferences right now.";
      setError(detail);
      pushToast({
        title: "Save failed",
        message: detail,
        tone: "error",
      });
    } finally {
      setSavingPreferences(false);
    }
  };

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">Notifications</div>
          <h2 className="surface-title">Notification center</h2>
          <p className="surface-copy">
            Review notification history and update delivery preferences.
          </p>
        </div>
        <div className="button-row">
          <label className="checkbox-row">
            <input
              checked={unreadOnly}
              onChange={(event) => setUnreadOnly(event.target.checked)}
              type="checkbox"
            />
            <span>Unread only</span>
          </label>
          <button
            className="button button-secondary"
            onClick={() => setRefreshTick((current) => current + 1)}
          >
            {status === "loading" ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </article>

      {error ? <InlineAlert title="Notifications unavailable" message={error} /> : null}

      <div className="dashboard-grid">
        <article className="surface-card">
          <div className="panel-header">
            <div>
              <h3 className="section-title">History</h3>
              <p className="surface-copy">Notification events returned by the backend.</p>
            </div>
          </div>

          {status === "ready" && visibleNotifications.length ? (
            <div className="list-stack">
              {visibleNotifications.map((notification) => (
                <div className="list-item list-item-block" key={notification.id}>
                  <div className="panel-header">
                    <div>
                      <div className="list-title">{notification.title}</div>
                      <div className="list-meta">
                        {notification.notification_type} | {notification.priority} |{" "}
                        {formatDate(notification.created_at)}
                      </div>
                    </div>
                    <div className="button-row">
                      {notification.is_read ? (
                        <div className="pill">Read</div>
                      ) : (
                        <button
                          className="button button-ghost"
                          onClick={() => void handleMarkRead(notification.id)}
                          type="button"
                        >
                          Mark read
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="list-body">{notification.body}</div>
                  <div className="list-meta">
                    Channel {notification.channel} | Sent {formatDate(notification.sent_at)}
                  </div>
                </div>
              ))}
            </div>
          ) : status === "ready" ? (
            <p className="list-body">No notifications match the current filter.</p>
          ) : (
            <p className="list-body">Loading notifications...</p>
          )}
        </article>

        <article className="surface-card">
          <div className="panel-header">
            <div>
              <h3 className="section-title">Preferences</h3>
              <p className="surface-copy">Delivery switches and per-type controls.</p>
            </div>
          </div>

          {preferences ? (
            <div className="form-stack">
              <label className="checkbox-row">
                <input
                  checked={preferences.notifications_enabled}
                  onChange={(event) =>
                    setPreferences((current) =>
                      current
                        ? { ...current, notifications_enabled: event.target.checked }
                        : current,
                    )
                  }
                  type="checkbox"
                />
                <span>Notifications enabled</span>
              </label>
              <label className="checkbox-row">
                <input
                  checked={preferences.in_app_enabled}
                  onChange={(event) =>
                    setPreferences((current) =>
                      current ? { ...current, in_app_enabled: event.target.checked } : current,
                    )
                  }
                  type="checkbox"
                />
                <span>In-app delivery</span>
              </label>
              <label className="checkbox-row">
                <input
                  checked={preferences.push_enabled}
                  onChange={(event) =>
                    setPreferences((current) =>
                      current ? { ...current, push_enabled: event.target.checked } : current,
                    )
                  }
                  type="checkbox"
                />
                <span>Push-ready delivery</span>
              </label>
              <label className="checkbox-row">
                <input
                  checked={preferences.email_enabled}
                  onChange={(event) =>
                    setPreferences((current) =>
                      current ? { ...current, email_enabled: event.target.checked } : current,
                    )
                  }
                  type="checkbox"
                />
                <span>Email delivery</span>
              </label>
              <label className="checkbox-row">
                <input
                  checked={preferences.sms_enabled}
                  onChange={(event) =>
                    setPreferences((current) =>
                      current ? { ...current, sms_enabled: event.target.checked } : current,
                    )
                  }
                  type="checkbox"
                />
                <span>SMS delivery</span>
              </label>

              <div className="preferences-grid">
                {notificationTypeLabels.map((item) => (
                  <label className="checkbox-row" key={item.key}>
                    <input
                      checked={Boolean(preferences.enabled_types[item.key])}
                      onChange={(event) =>
                        setPreferences((current) =>
                          current
                            ? {
                                ...current,
                                enabled_types: {
                                  ...current.enabled_types,
                                  [item.key]: event.target.checked,
                                },
                              }
                            : current,
                        )
                      }
                      type="checkbox"
                    />
                    <span>{item.label}</span>
                  </label>
                ))}
              </div>

              <div className="form-grid">
                <label className="field">
                  <span className="field-label">Timezone</span>
                  <input
                    className="input"
                    onChange={(event) =>
                      setPreferences((current) =>
                        current ? { ...current, timezone: event.target.value } : current,
                      )
                    }
                    value={preferences.timezone}
                  />
                </label>
                <label className="field">
                  <span className="field-label">Quiet hours start</span>
                  <input
                    className="input"
                    onChange={(event) =>
                      setPreferences((current) =>
                        current
                          ? { ...current, quiet_hours_start: event.target.value || null }
                          : current,
                      )
                    }
                    placeholder="22:00"
                    value={preferences.quiet_hours_start || ""}
                  />
                </label>
                <label className="field">
                  <span className="field-label">Quiet hours end</span>
                  <input
                    className="input"
                    onChange={(event) =>
                      setPreferences((current) =>
                        current
                          ? { ...current, quiet_hours_end: event.target.value || null }
                          : current,
                      )
                    }
                    placeholder="06:00"
                    value={preferences.quiet_hours_end || ""}
                  />
                </label>
              </div>

              <label className="checkbox-row">
                <input
                  checked={preferences.quiet_hours_enabled}
                  onChange={(event) =>
                    setPreferences((current) =>
                      current
                        ? { ...current, quiet_hours_enabled: event.target.checked }
                        : current,
                    )
                  }
                  type="checkbox"
                />
                <span>Enable quiet hours</span>
              </label>

              <div className="button-row">
                <div className="list-meta">
                  Last updated {formatDate(preferences.updated_at)}
                </div>
                <button
                  className="button button-primary"
                  disabled={savingPreferences}
                  onClick={() => void handleSavePreferences()}
                  type="button"
                >
                  {savingPreferences ? "Saving..." : "Save preferences"}
                </button>
              </div>
            </div>
          ) : (
            <p className="list-body">Loading notification preferences...</p>
          )}
        </article>
      </div>
    </section>
  );
}
