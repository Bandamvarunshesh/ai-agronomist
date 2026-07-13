import { useEffect, useState, type FormEvent } from "react";

import { useAuth } from "../../auth/auth-store";
import { EmptyState, InlineAlert, PageSkeleton } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";
import {
  changePassword,
  getProfile,
  updateProfile,
  type UserProfile,
} from "../../lib/api/account";
import { listFarms, type Farm } from "../../lib/api/farms";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}

export function ProfilePage() {
  const { state, retrySession } = useAuth();
  const { pushToast } = useToast();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "" });

  useEffect(() => {
    if (!state.token) {
      return;
    }

    let cancelled = false;
    const load = async () => {
      setStatus("loading");
      setError(null);
      try {
        const [profileResponse, farmsResponse] = await Promise.allSettled([
          getProfile(state.token!),
          state.user?.role === "farmer" ? listFarms(state.token!) : Promise.resolve([]),
        ]);
        if (cancelled) {
          return;
        }
        if (profileResponse.status !== "fulfilled") {
          throw profileResponse.reason;
        }
        setProfile(profileResponse.value);
        setFarms(farmsResponse.status === "fulfilled" ? farmsResponse.value : []);
        setStatus("ready");
      } catch {
        if (!cancelled) {
          setError("Unable to load your profile. Please try again.");
          setStatus("error");
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [state.token, state.user?.role]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!state.token || !profile) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await updateProfile(state.token, {
        full_name: profile.full_name || null,
        phone_number: profile.phone_number || null,
        preferred_language: profile.preferred_language,
        profile_picture_url: profile.profile_picture_url || null,
        default_state: profile.default_state || null,
        default_district: profile.default_district || null,
        default_farm_id: profile.default_farm_id || null,
      });
      setProfile(updated);
      await retrySession();
      pushToast({ title: "Profile saved", message: "Your profile was updated.", tone: "success" });
    } catch {
      setError("Unable to save your profile. Check the details and try again.");
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async () => {
    if (!state.token || !passwords.current_password || !passwords.new_password) {
      return;
    }
    setPasswordSaving(true);
    setError(null);
    try {
      await changePassword(state.token, passwords);
      setPasswords({ current_password: "", new_password: "" });
      pushToast({ title: "Password changed", message: "Your password was updated.", tone: "success" });
    } catch {
      setError("Unable to change password. Check your current password and try again.");
    } finally {
      setPasswordSaving(false);
    }
  };

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">Account</div>
          <h2 className="surface-title">Profile</h2>
          <p className="surface-copy">Manage your personal account details and default farming context.</p>
        </div>
      </article>

      {error ? <InlineAlert title="Profile action failed" message={error} /> : null}
      {status === "loading" ? <PageSkeleton title="Loading profile" /> : null}
      {status === "error" ? (
        <EmptyState
          eyebrow="Profile unavailable"
          title="We could not load your profile."
          message="Use the retry action to request the profile again."
          action={<button className="button button-primary" onClick={() => window.location.reload()} type="button">Retry</button>}
        />
      ) : null}

      {profile ? (
        <>
          <form className="surface-card form-stack" onSubmit={handleSubmit}>
            <div className="form-grid">
              <label className="field">
                <span className="field-label">Full name</span>
                <input className="input" value={profile.full_name || ""} onChange={(event) => setProfile((current) => current ? { ...current, full_name: event.target.value } : current)} />
              </label>
              <label className="field">
                <span className="field-label">Email</span>
                <input className="input" disabled value={profile.email || ""} />
              </label>
              <label className="field">
                <span className="field-label">Phone number</span>
                <input className="input" value={profile.phone_number || ""} onChange={(event) => setProfile((current) => current ? { ...current, phone_number: event.target.value } : current)} />
              </label>
              <label className="field">
                <span className="field-label">Preferred language</span>
                <select className="input select-input" value={profile.preferred_language} onChange={(event) => setProfile((current) => current ? { ...current, preferred_language: event.target.value } : current)}>
                  <option value="en">English</option>
                  <option value="hi">Hindi</option>
                  <option value="ta">Tamil</option>
                  <option value="te">Telugu</option>
                  <option value="kn">Kannada</option>
                  <option value="mr">Marathi</option>
                </select>
              </label>
              <label className="field">
                <span className="field-label">Default state</span>
                <input className="input" value={profile.default_state || ""} onChange={(event) => setProfile((current) => current ? { ...current, default_state: event.target.value } : current)} />
              </label>
              <label className="field">
                <span className="field-label">Default district</span>
                <input className="input" value={profile.default_district || ""} onChange={(event) => setProfile((current) => current ? { ...current, default_district: event.target.value } : current)} />
              </label>
              <label className="field">
                <span className="field-label">Default farm</span>
                <select className="input select-input" value={profile.default_farm_id || ""} onChange={(event) => setProfile((current) => current ? { ...current, default_farm_id: event.target.value || null } : current)}>
                  <option value="">No default farm</option>
                  {farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.farm_name}</option>)}
                </select>
              </label>
              <label className="field">
                <span className="field-label">Profile picture URL</span>
                <input className="input" value={profile.profile_picture_url || ""} onChange={(event) => setProfile((current) => current ? { ...current, profile_picture_url: event.target.value } : current)} />
              </label>
            </div>
            <div className="detail-grid">
              <div><div className="detail-label">Role</div><p className="detail-value">{profile.role}</p></div>
              <div><div className="detail-label">Account created</div><p className="detail-value">{formatDate(profile.created_at)}</p></div>
            </div>
            <div className="button-row">
              <button className="button button-primary" disabled={saving} type="submit">{saving ? "Saving..." : "Save profile"}</button>
            </div>
          </form>

          <article className="surface-card form-stack">
            <div>
              <div className="eyebrow">Security</div>
              <h3 className="surface-title">Change password</h3>
            </div>
            <div className="form-grid">
              <label className="field">
                <span className="field-label">Current password</span>
                <input className="input" type="password" value={passwords.current_password} onChange={(event) => setPasswords((current) => ({ ...current, current_password: event.target.value }))} />
              </label>
              <label className="field">
                <span className="field-label">New password</span>
                <input className="input" minLength={8} type="password" value={passwords.new_password} onChange={(event) => setPasswords((current) => ({ ...current, new_password: event.target.value }))} />
              </label>
            </div>
            <div className="button-row">
              <button className="button button-secondary" disabled={passwordSaving || !passwords.current_password || passwords.new_password.length < 8} onClick={() => void handlePasswordChange()} type="button">
                {passwordSaving ? "Updating..." : "Change password"}
              </button>
            </div>
          </article>
        </>
      ) : null}
    </section>
  );
}
