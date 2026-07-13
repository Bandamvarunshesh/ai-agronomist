import { useEffect, useState, type FormEvent } from "react";

import { useAuth } from "../../auth/auth-store";
import { EmptyState, InlineAlert, PageSkeleton, PermissionDeniedState } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";
import {
  createAdminEscalationContact,
  listAdminEscalationContacts,
  updateAdminEscalationContact,
  type EscalationContactInput,
} from "../../lib/api/admin";
import type { EscalationContact } from "../../lib/api/intelligence";

const emptyContact: EscalationContactInput = {
  name: "",
  organization: "",
  role: "",
  contact_type: "agronomist",
  phone_number: "",
  email: "",
  state: "",
  district: "",
  preferred_channel: "phone",
  contact_priority: 100,
  is_active: true,
  is_fallback: false,
  notes: "",
  service_area: { country: "India", languages: [] },
};

export function AdminEscalationContactsPage() {
  const { state } = useAuth();
  const { pushToast } = useToast();
  const [contacts, setContacts] = useState<EscalationContact[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<EscalationContactInput>(emptyContact);
  const [countryText, setCountryText] = useState("India");
  const [languageText, setLanguageText] = useState("");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    if (!state.token) return;
    setStatus("loading");
    try {
      setContacts(await listAdminEscalationContacts(state.token));
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  };

  useEffect(() => {
    if (state.user?.role === "admin") {
      void load();
    }
  }, [state.token, state.user?.role]);

  if (state.user?.role !== "admin") {
    return <PermissionDeniedState message="Escalation contact management requires an admin account." />;
  }

  const editContact = (contact: EscalationContact) => {
    setEditingId(contact.id);
    const languages = Array.isArray(contact.service_area.languages)
      ? contact.service_area.languages.map(String).join(", ")
      : "";
    const country =
      typeof contact.service_area.country === "string"
        ? contact.service_area.country
        : "India";
    setLanguageText(languages);
    setCountryText(country);
    setForm({
      name: contact.name,
      organization: contact.organization || "",
      role: contact.role || "",
      contact_type: contact.contact_type,
      phone_number: contact.phone_number || "",
      email: contact.email || "",
      state: contact.state || "",
      district: contact.district || "",
      preferred_channel: contact.preferred_channel,
      contact_priority: contact.contact_priority,
      is_active: contact.is_active,
      is_fallback: contact.is_fallback,
      notes: contact.notes || "",
      service_area: {},
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!state.token) return;
    setSaving(true);
    const payload = {
      ...form,
      organization: form.organization || null,
      role: form.role || null,
      phone_number: form.phone_number || null,
      email: form.email || null,
      state: form.state || null,
      district: form.district || null,
      notes: form.notes || null,
      service_area: {
        ...(form.service_area || {}),
        country: countryText,
        languages: languageText.split(",").map((language) => language.trim()).filter(Boolean),
      },
    };
    try {
      if (editingId) {
        await updateAdminEscalationContact(state.token, editingId, payload);
      } else {
        await createAdminEscalationContact(state.token, payload);
      }
      pushToast({ title: "Contact saved", message: "Escalation routing contact was updated.", tone: "success" });
      setEditingId(null);
      setForm(emptyContact);
      setCountryText("India");
      setLanguageText("");
      await load();
    } catch {
      pushToast({ title: "Contact save failed", message: "Unable to save the escalation contact.", tone: "error" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div><div className="eyebrow">Management</div><h2 className="surface-title">Escalation contacts</h2><p className="surface-copy">Manage district, state, and fallback contacts used by farmer escalation routing.</p></div>
      </article>

      <form className="surface-card form-stack" onSubmit={handleSubmit}>
        <h3 className="section-title">{editingId ? "Edit contact" : "Create contact"}</h3>
        <div className="form-grid">
          <label className="field"><span className="field-label">Name</span><input className="input" required value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} /></label>
          <label className="field"><span className="field-label">Organization</span><input className="input" value={form.organization || ""} onChange={(event) => setForm((current) => ({ ...current, organization: event.target.value }))} /></label>
          <label className="field"><span className="field-label">Role/contact type</span><input className="input" value={form.role || ""} onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))} /></label>
          <label className="field"><span className="field-label">Contact category</span><select className="input select-input" value={form.contact_type} onChange={(event) => setForm((current) => ({ ...current, contact_type: event.target.value }))}><option value="kvk">KVK</option><option value="agronomist">Agronomist</option><option value="govt_extension">Government extension</option><option value="vet">Veterinary</option><option value="emergency">Emergency</option></select></label>
          <label className="field"><span className="field-label">Phone</span><input className="input" value={form.phone_number || ""} onChange={(event) => setForm((current) => ({ ...current, phone_number: event.target.value }))} /></label>
          <label className="field"><span className="field-label">Email</span><input className="input" type="email" value={form.email || ""} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} /></label>
          <label className="field"><span className="field-label">Country</span><input className="input" value={countryText} onChange={(event) => setCountryText(event.target.value)} /></label>
          <label className="field"><span className="field-label">State</span><input className="input" value={form.state || ""} onChange={(event) => setForm((current) => ({ ...current, state: event.target.value }))} /></label>
          <label className="field"><span className="field-label">District</span><input className="input" value={form.district || ""} onChange={(event) => setForm((current) => ({ ...current, district: event.target.value }))} /></label>
          <label className="field"><span className="field-label">Languages</span><input className="input" value={languageText} onChange={(event) => setLanguageText(event.target.value)} /></label>
          <label className="field"><span className="field-label">Priority</span><input className="input" min="0" type="number" value={form.contact_priority} onChange={(event) => setForm((current) => ({ ...current, contact_priority: Number(event.target.value) || 0 }))} /></label>
          <label className="field"><span className="field-label">Availability notes</span><input className="input" value={form.notes || ""} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} /></label>
          <label className="checkbox-row align-end"><input checked={Boolean(form.is_active)} onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))} type="checkbox" /><span>Active</span></label>
          <label className="checkbox-row align-end"><input checked={Boolean(form.is_fallback)} onChange={(event) => setForm((current) => ({ ...current, is_fallback: event.target.checked }))} type="checkbox" /><span>Fallback routing</span></label>
        </div>
        <div className="button-row">
          <button className="button button-primary" disabled={saving || !form.name || (!form.phone_number && !form.email)} type="submit">{saving ? "Saving..." : editingId ? "Save contact" : "Create contact"}</button>
          {editingId ? <button className="button button-ghost" onClick={() => { setEditingId(null); setForm(emptyContact); setCountryText("India"); setLanguageText(""); }} type="button">Cancel edit</button> : null}
        </div>
      </form>

      {status === "loading" ? <PageSkeleton title="Loading contacts" /> : null}
      {status === "error" ? <InlineAlert title="Contacts unavailable" message="Unable to load escalation contacts." action={<button className="button button-primary" onClick={() => void load()} type="button">Retry</button>} /> : null}
      {status === "ready" && !contacts.length ? <EmptyState title="No escalation contacts configured." message="Create a district, state, or fallback contact before farmers request expert support." /> : null}
      {contacts.length ? (
        <article className="surface-card">
          <div className="list-stack">
            {contacts.map((contact) => (
              <div className="list-item list-item-block" key={contact.id}>
                <div className="list-row"><div className="list-title">{contact.name}</div><div className={contact.is_active ? "pill pill-strong" : "pill"}>{contact.is_active ? "Active" : "Inactive"}</div></div>
                <div className="list-meta">{contact.contact_type} | {contact.district || "State/general"} | {contact.state || "National"} | Priority {contact.contact_priority}</div>
                <p className="list-body">{contact.organization || "No organization"} | {contact.phone_number || contact.email}</p>
                <div className="button-row">
                  <button className="button button-secondary" onClick={() => editContact(contact)} type="button">Edit</button>
                  <button
                    className="button button-ghost"
                    onClick={() =>
                      void updateAdminEscalationContact(state.token!, contact.id, {
                        name: contact.name,
                        contact_type: contact.contact_type,
                        role: contact.role,
                        organization: contact.organization,
                        district: contact.district,
                        state: contact.state,
                        phone_number: contact.phone_number,
                        email: contact.email,
                        preferred_channel: contact.preferred_channel,
                        contact_priority: contact.contact_priority,
                        is_fallback: contact.is_fallback,
                        notes: contact.notes,
                        is_active: false,
                        service_area: {},
                      }).then(load)
                    }
                    type="button"
                  >
                    Deactivate
                  </button>
                </div>
              </div>
            ))}
          </div>
        </article>
      ) : null}
    </section>
  );
}
