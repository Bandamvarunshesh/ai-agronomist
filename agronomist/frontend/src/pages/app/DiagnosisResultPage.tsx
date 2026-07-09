import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { InlineAlert } from "../../components/ui/Feedback";
import {
  readDiagnosisResult,
  storeDiagnosisResult,
  type DiagnosisResultBundle,
} from "../../lib/api/diagnosis";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatConfidence(value: number) {
  return `${Math.round(value * 100)}%`;
}

function renderList(items: string[], emptyMessage: string) {
  if (!items.length) {
    return <p className="list-body">{emptyMessage}</p>;
  }

  return (
    <ul className="result-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function DiagnosisResultPage() {
  const { farmId = "", diagnosisId = "" } = useParams();
  const location = useLocation();
  const routeState = location.state as DiagnosisResultBundle | null;
  const [bundle, setBundle] = useState<DiagnosisResultBundle | null>(() => {
    if (routeState?.diagnosis?.id === diagnosisId) {
      return routeState;
    }
    return readDiagnosisResult(diagnosisId);
  });

  useEffect(() => {
    if (routeState?.diagnosis?.id === diagnosisId) {
      storeDiagnosisResult(routeState);
      setBundle(routeState);
      return;
    }

    setBundle(readDiagnosisResult(diagnosisId));
  }, [diagnosisId, routeState]);

  const diagnosis = bundle?.diagnosis || null;
  const farm = bundle?.farm || null;
  const image = bundle?.image || null;

  const severityTone = useMemo(() => {
    const normalized = diagnosis?.severity.toLowerCase() || "";
    if (normalized.includes("high") || normalized.includes("critical")) {
      return "pill pill-strong";
    }
    return "pill";
  }, [diagnosis?.severity]);

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">Diagnosis result</div>
          <h2 className="surface-title">
            {diagnosis ? diagnosis.disease_name : "Diagnosis unavailable"}
          </h2>
          <p className="surface-copy">
            Review the result returned by the existing diagnosis API for this farm image.
          </p>
        </div>
        <div className="button-row">
          <Link className="button button-ghost button-link" to={`/app/farms/${farmId}`}>
            Back to farm
          </Link>
          <Link
            className="button button-primary button-link"
            to={`/app/farms/${farmId}/diagnosis`}
          >
            New diagnosis
          </Link>
        </div>
      </article>

      {!diagnosis ? (
        <InlineAlert
          title="Diagnosis result unavailable"
          message="This browser no longer has the diagnosis response cached. Run the diagnosis again from the farm diagnosis page to view a fresh result."
        />
      ) : (
        <>
          <div className="metric-grid">
            <article className="metric-card">
              <div className="metric-label">Disease</div>
              <div className="metric-value diagnosis-metric">{diagnosis.disease_name}</div>
            </article>
            <article className="metric-card">
              <div className="metric-label">Confidence</div>
              <div className="metric-value">{formatConfidence(diagnosis.confidence_score)}</div>
            </article>
            <article className="metric-card">
              <div className="metric-label">Severity</div>
              <div className="metric-value">
                <span className={severityTone}>{diagnosis.severity}</span>
              </div>
            </article>
            <article className="metric-card">
              <div className="metric-label">Human escalation</div>
              <div className="metric-value">
                {diagnosis.escalate_to_human ? "Recommended" : "Not flagged"}
              </div>
            </article>
          </div>

          <div className="dashboard-grid">
            <article className="surface-card">
              <h3 className="section-title">Context</h3>
              <div className="detail-grid">
                <div>
                  <div className="detail-label">Farm</div>
                  <p className="detail-value">{farm?.farm_name || diagnosis.farm_id}</p>
                </div>
                <div>
                  <div className="detail-label">Crop</div>
                  <p className="detail-value">{farm?.crop || "Not available"}</p>
                </div>
                <div>
                  <div className="detail-label">Image</div>
                  <p className="detail-value">
                    {image?.original_filename || diagnosis.crop_image_id}
                  </p>
                </div>
                <div>
                  <div className="detail-label">Created</div>
                  <p className="detail-value">{formatDate(diagnosis.created_at)}</p>
                </div>
              </div>
            </article>

            <article className="surface-card">
              <h3 className="section-title">Possible causes</h3>
              {renderList(
                diagnosis.possible_causes,
                "The diagnosis response did not include possible causes.",
              )}
            </article>

            <article className="surface-card">
              <h3 className="section-title">Organic treatment</h3>
              {renderList(
                diagnosis.organic_treatment,
                "No organic treatment advice was returned.",
              )}
            </article>

            <article className="surface-card">
              <h3 className="section-title">Chemical treatment</h3>
              {renderList(
                diagnosis.chemical_treatment,
                "No chemical treatment advice was returned.",
              )}
            </article>

            <article className="surface-card dashboard-span-two">
              <h3 className="section-title">Prevention steps</h3>
              {renderList(
                diagnosis.prevention_steps,
                "No prevention steps were returned.",
              )}
            </article>
          </div>
        </>
      )}
    </section>
  );
}
