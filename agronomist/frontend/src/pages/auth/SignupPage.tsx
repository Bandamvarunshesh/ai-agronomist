import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { InlineAlert } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";

export function SignupPage() {
  const { state, signup, clearError } = useAuth();
  const { pushToast } = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone_number: "",
    preferred_language: "en",
    password: "",
  });

  useEffect(() => {
    if (state.status === "authenticated") {
      navigate("/app", { replace: true });
    }
  }, [navigate, state.status]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    clearError();

    try {
      await signup({
        full_name: form.full_name || null,
        email: form.email,
        phone_number: form.phone_number || null,
        preferred_language: form.preferred_language,
        password: form.password,
      });
      pushToast({
        title: "Account created",
        message: "You are signed in and ready to use the app shell.",
        tone: "success",
      });
    } catch (error) {
      pushToast({
        title: "Sign-up failed",
        message:
          error instanceof Error
            ? error.message
            : "Unable to create your account right now.",
        tone: "error",
      });
    }
  };

  return (
    <div className="form-stack">
      <div>
        <h2 className="section-title">Create account</h2>
        <p className="section-copy">
          This foundation uses the backend signup and login flow directly.
        </p>
      </div>

      {state.error ? (
        <InlineAlert
          title="Registration error"
          message={state.error}
        />
      ) : null}

      <form className="form-stack" onSubmit={handleSubmit}>
        <label className="field">
          <span className="field-label">Full name</span>
          <input
            className="input"
            type="text"
            autoComplete="name"
            value={form.full_name}
            onChange={(event) =>
              setForm((current) => ({ ...current, full_name: event.target.value }))
            }
          />
        </label>

        <label className="field">
          <span className="field-label">Email</span>
          <input
            className="input"
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={(event) =>
              setForm((current) => ({ ...current, email: event.target.value }))
            }
            required
          />
        </label>

        <label className="field">
          <span className="field-label">Phone number</span>
          <input
            className="input"
            type="tel"
            autoComplete="tel"
            value={form.phone_number}
            onChange={(event) =>
              setForm((current) => ({ ...current, phone_number: event.target.value }))
            }
          />
        </label>

        <label className="field">
          <span className="field-label">Preferred language</span>
          <input
            className="input"
            type="text"
            value={form.preferred_language}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                preferred_language: event.target.value,
              }))
            }
            required
          />
        </label>

        <label className="field">
          <span className="field-label">Password</span>
          <input
            className="input"
            type="password"
            autoComplete="new-password"
            minLength={8}
            value={form.password}
            onChange={(event) =>
              setForm((current) => ({ ...current, password: event.target.value }))
            }
            required
          />
        </label>

        <button
          className="button button-primary button-block"
          disabled={state.isSubmitting}
          type="submit"
        >
          {state.isSubmitting ? "Creating account..." : "Create account"}
        </button>
      </form>

      <div className="footer-copy">
        Already registered? <Link to="/login">Sign in</Link>
      </div>
    </div>
  );
}
