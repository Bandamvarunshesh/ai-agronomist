import type { ReactNode } from "react";

export function FullPageLoader({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="feedback-shell">
      <div className="spinner" aria-hidden="true" />
      <div className="feedback-title">{title}</div>
      <div className="feedback-message">{message}</div>
    </div>
  );
}

export function InlineAlert({
  title,
  message,
  tone = "error",
  action,
}: {
  title: string;
  message: string;
  tone?: "error" | "warning" | "info";
  action?: ReactNode;
}) {
  return (
    <div className={`inline-alert inline-alert-${tone}`} role="alert">
      <div className="inline-alert-title">{title}</div>
      <div className="inline-alert-message">{message}</div>
      {action ? <div className="inline-alert-action">{action}</div> : null}
    </div>
  );
}
