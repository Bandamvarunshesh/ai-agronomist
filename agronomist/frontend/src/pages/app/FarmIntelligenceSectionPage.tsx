import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { FarmIntelligenceNav } from "../../components/farms/FarmIntelligenceNav";
import { EmptyState, InlineAlert, PageSkeleton } from "../../components/ui/Feedback";
import {
  getFarmAdvisories,
  getFarmMarket,
  getFarmNews,
  getFarmSoil,
  type FarmIntelligenceResponse,
} from "../../lib/api/intelligence";

type SectionKind = "advisories" | "news" | "market" | "soil";

const config = {
  advisories: {
    eyebrow: "Farm intelligence",
    title: "Advisories",
    empty: "No government advisories are available for this farm yet.",
  },
  news: {
    eyebrow: "Farm intelligence",
    title: "Agricultural news",
    empty: "No agricultural news is available for this farm yet.",
  },
  market: {
    eyebrow: "Farm intelligence",
    title: "Market prices",
    empty: "No market prices are available for this crop and location yet.",
  },
  soil: {
    eyebrow: "Farm intelligence",
    title: "Soil information",
    empty: "No soil information is available for this farm yet.",
  },
} satisfies Record<SectionKind, { eyebrow: string; title: string; empty: string }>;

export function FarmIntelligenceSectionPage({ kind }: { kind: SectionKind }) {
  const { farmId = "" } = useParams();
  const { state } = useAuth();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [data, setData] = useState<FarmIntelligenceResponse | null>(null);

  const load = async () => {
    if (!state.token || !farmId) return;
    setStatus("loading");
    try {
      const loaders = {
        advisories: getFarmAdvisories,
        news: getFarmNews,
        market: getFarmMarket,
        soil: getFarmSoil,
      };
      setData(await loaders[kind](state.token, farmId));
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  };

  useEffect(() => {
    if (state.status === "authenticated") {
      void load();
    }
  }, [farmId, kind, state.status, state.token]);

  const items = useMemo(() => {
    if (!data) return [];
    if (kind === "advisories") return data.government_advisories || [];
    if (kind === "news") return data.news || [];
    if (kind === "market") return data.market || [];
    if (kind === "soil") return data.soil ? [data.soil] : [];
    return [];
  }, [data, kind]);

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">{config[kind].eyebrow}</div>
          <h2 className="surface-title">{config[kind].title}</h2>
          <p className="surface-copy">{data ? `${data.farm_name} | ${data.crop}` : "Farm-specific intelligence from configured sources."}</p>
        </div>
        <button className="button button-secondary" onClick={() => void load()} type="button">Refresh</button>
      </article>
      {farmId ? <FarmIntelligenceNav farmId={farmId} /> : null}
      {status === "loading" ? <PageSkeleton title={`Loading ${config[kind].title.toLowerCase()}`} /> : null}
      {status === "error" ? <InlineAlert title={`${config[kind].title} unavailable`} message="Unable to load this farm intelligence section right now." action={<button className="button button-primary" onClick={() => void load()} type="button">Retry</button>} /> : null}
      {status === "ready" && !items.length ? <EmptyState title={config[kind].empty} message="When trusted providers return matching information, it will appear here." /> : null}
      {items.length ? (
        <article className="surface-card">
          <div className="list-stack">
            {items.map((item, index) => (
              <div className="list-item list-item-block" key={`${kind}-${index}`}>
                <div className="list-title">
                  {"title" in item ? item.title : "market" in item ? item.market : "Soil profile"}
                </div>
                <div className="list-meta">
                  {"source_name" in item ? item.source_name : "Source"}{" "}
                  {"published_at" in item && item.published_at ? `| ${item.published_at}` : ""}
                  {"price" in item && item.price !== null ? `| ${item.price} ${item.unit || ""}` : ""}
                </div>
                <p className="list-body">
                  {"summary" in item
                    ? item.summary || item.url
                    : "soil_type" in item
                      ? `${item.soil_type || "Soil"} ${item.ph !== null ? `| pH ${item.ph}` : ""}`
                      : "No details available."}
                </p>
              </div>
            ))}
          </div>
        </article>
      ) : null}
    </section>
  );
}
