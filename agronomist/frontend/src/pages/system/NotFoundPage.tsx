import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="route-shell">
      <div className="surface-card surface-card-centered">
        <div className="eyebrow">404</div>
        <h1 className="surface-title">This route is not part of the foundation.</h1>
        <p className="surface-copy">
          Head back to the current app shell and keep building from there.
        </p>
        <Link className="button button-primary" to="/">
          Go home
        </Link>
      </div>
    </div>
  );
}
