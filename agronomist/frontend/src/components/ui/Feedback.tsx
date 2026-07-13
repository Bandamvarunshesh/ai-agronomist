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

export function PageSkeleton({
  title = "Loading",
  lines = 3,
}: {
  title?: string;
  lines?: number;
}) {
  return (
    <article className="surface-card skeleton-card" aria-busy="true">
      <div className="skeleton-line skeleton-title" />
      <div className="eyebrow">{title}</div>
      {Array.from({ length: lines }).map((_, index) => (
        <div className="skeleton-line" key={index} />
      ))}
    </article>
  );
}

export function EmptyState({
  eyebrow = "Empty",
  title,
  message,
  action,
}: {
  eyebrow?: string;
  title: string;
  message: string;
  action?: ReactNode;
}) {
  return (
    <article className="surface-card empty-state">
      <div className="eyebrow">{eyebrow}</div>
      <h3 className="surface-title">{title}</h3>
      <p className="surface-copy">{message}</p>
      {action ? <div className="button-row">{action}</div> : null}
    </article>
  );
}

export function PermissionDeniedState({
  message = "You do not have permission to view this page.",
}: {
  message?: string;
}) {
  return (
    <InlineAlert
      title="Permission denied"
      message={message}
      tone="warning"
    />
  );
}
