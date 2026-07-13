import { useEffect, useState, type FormEvent } from "react";

import { SettingsLocationPicker } from "../../components/account/SettingsLocationPicker";
import { EmptyState, InlineAlert, PageSkeleton } from "../../components/ui/Feedback";
import { useTheme } from "../../components/ui/ThemeProvider";
import { useToast } from "../../components/ui/ToastProvider";
import { useAuth } from "../../auth/auth-store";
import {
  getAccountSettings,
  updateAccountSettings,
  type AccountSettings,
} from "../../lib/api/account";
import { getNotificationPreferences, updateNotificationPreferences } from "../../lib/api/intelligence";
import { listFarms, type Farm } from "../../lib/api/farms";

const notificationTypes = [
  ["weather_alert", "weather_alerts", "Weather alerts"],
  ["irrigation_reminder", "irrigation_reminders", "Irrigation reminders"],
  ["fertilizer_reminder", "fertilizer_reminders", "Fertilizer reminders"],
  ["disease_alert", "disease_alerts", "Disease alerts"],
  ["crop_stage_reminder", "crop_stage_reminders", "Crop-stage reminders"],
  ["high_risk_alert", "high_risk_alerts", "High-risk alerts"],
] as const;

export function SettingsPage() {
  const { state, retrySession } = useAuth();
  const { setTheme } = useTheme();
  const { pushToast } = useToast();
  const [settings, setSettings] = useState<AccountSettings | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!state.token) {
      return;
    }
    let cancelled = false;
    const load = async () => {
      setStatus("loading");
      setError(null);
      try {
        const [settingsResponse, notificationsResponse, farmsResponse] = await Promise.allSettled([
          getAccountSettings(state.token!),
          getNotificationPreferences(state.token!),
          state.user?.role === "farmer" ? listFarms(state.token!) : Promise.resolve([]),
        ]);
        if (cancelled) {
          return;
        }
        if (settingsResponse.status !== "fulfilled") {
          throw settingsResponse.reason;
        }
        const loaded = settingsResponse.value;
        if (notificationsResponse.status === "fulfilled") {
          const preferences = notificationsResponse.value;
          loaded.push_enabled = preferences.push_enabled;
          loaded.push_token = preferences.push_token;
          loaded.push_platform = preferences.push_platform;
          loaded.push_provider = preferences.push_provider;
          for (const [notificationKey, settingsKey] of notificationTypes) {
            loaded[settingsKey] = preferences.enabled_types[notificationKey] ?? loaded[settingsKey];
          }
          loaded.daily_summary = preferences.enabled_types.daily_ai_summary ?? loaded.daily_summary;
          loaded.weekly_summary = preferences.enabled_types.weekly_ai_summary ?? loaded.weekly_summary;
        }
        setSettings(loaded);
        setFarms(farmsResponse.status === "fulfilled" ? farmsResponse.value : []);
        setTheme(loaded.theme);
        setStatus("ready");
      } catch {
        if (!cancelled) {
          setError("Unable to load settings. Please try again.");
          setStatus("error");
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [setTheme, state.token, state.user?.role]);

  const updateValue = <K extends keyof AccountSettings>(key: K, value: AccountSettings[K]) => {
    setSettings((current) => current ? { ...current, [key]: value } : current);
  };

  const handleUseCurrentLocation = () => {
    if (!settings) {
      return;
    }
    if (!navigator.geolocation) {
      updateValue("location_permission_status", "unsupported");
      setError("This browser does not support current location.");
      return;
    }
    updateValue("location_permission_status", "prompt");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setSettings((current) =>
          current
            ? {
                ...current,
                default_location_latitude: Number(position.coords.latitude.toFixed(6)),
                default_location_longitude: Number(position.coords.longitude.toFixed(6)),
                location_source: "current_location",
                location_permission_status: "granted",
              }
            : current,
        );
      },
      (locationError) => {
        updateValue(
          "location_permission_status",
          locationError.code === locationError.PERMISSION_DENIED
            ? "denied"
            : locationError.code === locationError.TIMEOUT
              ? "timeout"
              : "unavailable",
        );
      },
      { enableHighAccuracy: true, maximumAge: 60000, timeout: 10000 },
    );
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!state.token || !settings) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await updateAccountSettings(state.token, settings);
      await updateNotificationPreferences(state.token, {
        push_enabled: settings.push_enabled,
        push_token: settings.push_token,
        push_platform: settings.push_platform,
        push_provider: settings.push_provider,
        timezone: settings.timezone,
        enabled_types: {
          weather_alert: settings.weather_alerts,
          irrigation_reminder: settings.irrigation_reminders,
          fertilizer_reminder: settings.fertilizer_reminders,
          disease_alert: settings.disease_alerts,
          crop_stage_reminder: settings.crop_stage_reminders,
          high_risk_alert: settings.high_risk_alerts,
          daily_ai_summary: settings.daily_summary,
          weekly_ai_summary: settings.weekly_summary,
        },
      });
      setSettings(updated);
      setTheme(updated.theme);
      await retrySession();
      pushToast({ title: "Settings saved", message: "Your preferences were updated.", tone: "success" });
    } catch {
      setError("Unable to save settings. Please review the fields and try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">Account</div>
          <h2 className="surface-title">Settings</h2>
          <p className="surface-copy">Store account, notification, AI, location, and privacy preferences in the backend.</p>
        </div>
      </article>

      {error ? <InlineAlert title="Settings action failed" message={error} tone="warning" /> : null}
      {status === "loading" ? <PageSkeleton title="Loading settings" lines={5} /> : null}
      {status === "error" ? (
        <EmptyState eyebrow="Settings unavailable" title="Settings could not be loaded." message="Retry from this page once the API is available." action={<button className="button button-primary" onClick={() => window.location.reload()} type="button">Retry</button>} />
      ) : null}

      {settings ? (
        <form className="form-stack" onSubmit={handleSubmit}>
          <article className="surface-card form-stack">
            <h3 className="section-title">General</h3>
            <div className="form-grid">
              <label className="field">
                <span className="field-label">Preferred language</span>
                <select className="input select-input" value={settings.preferred_language} onChange={(event) => updateValue("preferred_language", event.target.value)}>
                  <option value="en">English</option>
                  <option value="hi">Hindi</option>
                  <option value="ta">Tamil</option>
                  <option value="te">Telugu</option>
                  <option value="kn">Kannada</option>
                  <option value="mr">Marathi</option>
                </select>
              </label>
              <label className="field">
                <span className="field-label">Units</span>
                <select className="input select-input" value={settings.units} onChange={(event) => updateValue("units", event.target.value as AccountSettings["units"])}>
                  <option value="metric">Metric</option>
                  <option value="imperial">Imperial</option>
                </select>
              </label>
              <label className="field">
                <span className="field-label">Timezone</span>
                <input className="input" value={settings.timezone} onChange={(event) => updateValue("timezone", event.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Date format</span>
                <select className="input select-input" value={settings.date_format} onChange={(event) => updateValue("date_format", event.target.value as AccountSettings["date_format"])}>
                  <option value="dd-mm-yyyy">DD-MM-YYYY</option>
                  <option value="mm-dd-yyyy">MM-DD-YYYY</option>
                  <option value="yyyy-mm-dd">YYYY-MM-DD</option>
                </select>
              </label>
              <label className="field">
                <span className="field-label">Theme</span>
                <select className="input select-input" value={settings.theme} onChange={(event) => { const theme = event.target.value as AccountSettings["theme"]; updateValue("theme", theme); setTheme(theme); }}>
                  <option value="system">System</option>
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                </select>
              </label>
            </div>
          </article>

          <article className="surface-card form-stack">
            <div className="panel-header">
              <div>
                <h3 className="section-title">Location</h3>
                <p className="surface-copy">Set your default account location with current location, map selection, or manual fallback.</p>
              </div>
              <button className="button button-secondary" onClick={handleUseCurrentLocation} type="button">Use Current Location</button>
            </div>
            <div className="form-grid">
              <label className="field">
                <span className="field-label">Default state</span>
                <input className="input" value={settings.default_state || ""} onChange={(event) => updateValue("default_state", event.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Default district</span>
                <input className="input" value={settings.default_district || ""} onChange={(event) => updateValue("default_district", event.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Default farm</span>
                <select className="input select-input" value={settings.default_farm_id || ""} onChange={(event) => updateValue("default_farm_id", event.target.value || null)}>
                  <option value="">No default farm</option>
                  {farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.farm_name}</option>)}
                </select>
              </label>
              <label className="field">
                <span className="field-label">Default location</span>
                <input className="input" value={settings.default_location} onChange={(event) => updateValue("default_location", event.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Latitude</span>
                <input className="input" type="number" min="-90" max="90" step="0.000001" value={settings.default_location_latitude ?? ""} onChange={(event) => updateValue("default_location_latitude", event.target.value ? Number(event.target.value) : null)} />
              </label>
              <label className="field">
                <span className="field-label">Longitude</span>
                <input className="input" type="number" min="-180" max="180" step="0.000001" value={settings.default_location_longitude ?? ""} onChange={(event) => updateValue("default_location_longitude", event.target.value ? Number(event.target.value) : null)} />
              </label>
            </div>
            <div className="selected-coordinate-panel">
              <div><div className="detail-label">Permission status</div><div className="detail-value">{settings.location_permission_status}</div></div>
              <div><div className="detail-label">Location source</div><div className="detail-value">{settings.location_source}</div></div>
            </div>
            <SettingsLocationPicker
              latitude={settings.default_location_latitude}
              longitude={settings.default_location_longitude}
              onSelect={(position, source) => setSettings((current) => current ? {
                ...current,
                default_location_latitude: Number(position.lat.toFixed(6)),
                default_location_longitude: Number(position.lng.toFixed(6)),
                location_source: source,
              } : current)}
            />
          </article>

          <article className="surface-card form-stack">
            <h3 className="section-title">Notifications</h3>
            <div className="preferences-grid">
              {notificationTypes.map(([, key, label]) => (
                <label className="checkbox-row" key={key}>
                  <input checked={settings[key]} onChange={(event) => updateValue(key, event.target.checked)} type="checkbox" />
                  <span>{label}</span>
                </label>
              ))}
              <label className="checkbox-row"><input checked={settings.daily_summary} onChange={(event) => updateValue("daily_summary", event.target.checked)} type="checkbox" /><span>Daily summary</span></label>
              <label className="checkbox-row"><input checked={settings.weekly_summary} onChange={(event) => updateValue("weekly_summary", event.target.checked)} type="checkbox" /><span>Weekly summary</span></label>
              <label className="checkbox-row"><input checked={settings.push_enabled} onChange={(event) => updateValue("push_enabled", event.target.checked)} type="checkbox" /><span>Push ready</span></label>
            </div>
            <div className="form-grid">
              <label className="field"><span className="field-label">Push token</span><input className="input" value={settings.push_token || ""} onChange={(event) => updateValue("push_token", event.target.value)} /></label>
              <label className="field"><span className="field-label">Push platform</span><input className="input" value={settings.push_platform || ""} onChange={(event) => updateValue("push_platform", event.target.value)} /></label>
              <label className="field"><span className="field-label">Push provider</span><input className="input" value={settings.push_provider || ""} onChange={(event) => updateValue("push_provider", event.target.value)} /></label>
            </div>
          </article>

          <article className="surface-card form-stack">
            <h3 className="section-title">AI Preferences</h3>
            <div className="form-grid">
              <label className="field"><span className="field-label">Response language</span><input className="input" value={settings.response_language} onChange={(event) => updateValue("response_language", event.target.value)} /></label>
              <label className="field"><span className="field-label">Explanation detail</span><select className="input select-input" value={settings.explanation_detail} onChange={(event) => updateValue("explanation_detail", event.target.value as AccountSettings["explanation_detail"])}><option value="concise">Concise</option><option value="standard">Standard</option><option value="detailed">Detailed</option></select></label>
            </div>
            <div className="preferences-grid">
              <label className="checkbox-row"><input checked={settings.organic_treatment_preference} onChange={(event) => updateValue("organic_treatment_preference", event.target.checked)} type="checkbox" /><span>Organic treatment preference</span></label>
              <label className="checkbox-row"><input checked={settings.chemical_treatment_preference} onChange={(event) => updateValue("chemical_treatment_preference", event.target.checked)} type="checkbox" /><span>Chemical treatment preference</span></label>
              <label className="checkbox-row"><input checked={settings.show_sources_by_default} onChange={(event) => updateValue("show_sources_by_default", event.target.checked)} type="checkbox" /><span>Show sources by default</span></label>
              <label className="checkbox-row"><input checked={settings.allow_farm_context_in_chat} onChange={(event) => updateValue("allow_farm_context_in_chat", event.target.checked)} type="checkbox" /><span>Allow farm context in chat</span></label>
            </div>
          </article>

          <article className="surface-card form-stack">
            <h3 className="section-title">Privacy</h3>
            <InlineAlert title="AI data usage" message={settings.ai_data_usage_explanation} tone="info" />
            <div className="preferences-grid">
              <label className="checkbox-row"><input checked={settings.location_usage_consent} onChange={(event) => updateValue("location_usage_consent", event.target.checked)} type="checkbox" /><span>Location usage consent</span></label>
              <label className="checkbox-row"><input checked={settings.delete_account_requested} onChange={(event) => updateValue("delete_account_requested", event.target.checked)} type="checkbox" /><span>Request account deletion</span></label>
              <label className="checkbox-row"><input checked={settings.export_account_data_requested} onChange={(event) => updateValue("export_account_data_requested", event.target.checked)} type="checkbox" /><span>Request account data export</span></label>
            </div>
          </article>

          <div className="button-row">
            <button className="button button-primary" disabled={saving} type="submit">{saving ? "Saving..." : "Save settings"}</button>
          </div>
        </form>
      ) : null}
    </section>
  );
}
