import { useCallback, useEffect, useState } from "react";
import rawDataset from "./data/research-dataset.json";
import { ChartPatterns, NoticeList } from "./components";
import { parseHash, serializeHash } from "./hashState";
import type { AppState, Dataset, RouteId } from "./types";
import { Comparison } from "./views/Comparison";
import { Methods } from "./views/Methods";
import { Overview } from "./views/Overview";
import { Quality } from "./views/Quality";
import { Questions } from "./views/Questions";

const dataset = rawDataset as Dataset;
const NAV: { id: RouteId; label: string }[] = [
  { id: "yleiskuva", label: "Yleiskuva" },
  { id: "vertailu", label: "Hakustrategioiden vertailu" },
  { id: "kysymykset", label: "Kysymyskohtaiset tulokset" },
  { id: "laatu", label: "Laatu ja viive" },
  { id: "menetelmat", label: "Menetelmät ja rajoitukset" },
];

export function App() {
  const [hash, setHash] = useState(() => window.location.hash);
  const [stickyNotices, setStickyNotices] = useState<string[]>([]);
  const state = parseHash(hash, dataset);

  useEffect(() => {
    const sync = () => setHash(window.location.hash);
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);

  useEffect(() => {
    if (state.notices.length > 0) {
      setStickyNotices(state.notices);
    }
    const clean = serializeHash(state, dataset);
    if (clean !== hash) {
      const url = `${window.location.pathname}${window.location.search}${clean}`;
      window.history.replaceState(null, "", url);
      setHash(clean);
    }
  }, [hash, state]);

  const update = useCallback((partial: Partial<AppState>, mode: "push" | "replace" = "push") => {
    setStickyNotices([]);
    setHash((current) => {
      const parsed = parseHash(current, dataset);
      const next = { ...parsed, ...partial, notices: [] };
      const serialized = serializeHash(parseHash(serializeHash(next, dataset), dataset), dataset);
      if (serialized !== current) {
        const url = `${window.location.pathname}${window.location.search}${serialized}`;
        if (mode === "replace") {
          window.history.replaceState(null, "", url);
        } else {
          window.history.pushState(null, "", url);
        }
      }
      return serialized;
    });
  }, []);

  if (dataset.schema_version !== "1.0.0") {
    return <p role="alert">Tulosaineiston versio ei ole tuettu.</p>;
  }

  const notices = [...new Set([...stickyNotices, ...state.notices])];
  return (
    <>
      <a className="skip" href="#sisalto">
        Siirry sisältöön
      </a>
      <header className="site-header">
        <p className="eyebrow">{dataset.boundary.title_fi}</p>
        <p className="statement">{dataset.boundary.statement_fi}</p>
        <nav aria-label="Näkymät">
          <ul>
            {NAV.map((item) => (
              <li key={item.id}>
                <a
                  href={serializeHash({ ...state, route: item.id, notices: [] }, dataset)}
                  aria-current={state.route === item.id ? "page" : undefined}
                  onClick={() => setStickyNotices([])}
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      {dataset.validation.release_blocked ? (
        <p className="blocker" role="status">
          Julkaisutarkistus on kesken: {dataset.validation.release_block_reason_fi}
        </p>
      ) : null}
      <main id="sisalto">
        <NoticeList notices={notices} />
        <ChartPatterns />
        {state.route === "yleiskuva" ? <Overview dataset={dataset} /> : null}
        {state.route === "vertailu" ? <Comparison dataset={dataset} state={state} onRun={(run) => update({ run })} /> : null}
        {state.route === "kysymykset" ? <Questions dataset={dataset} state={state} onChange={update} /> : null}
        {state.route === "laatu" ? <Quality dataset={dataset} state={state} onChange={update} /> : null}
        {state.route === "menetelmat" ? <Methods dataset={dataset} /> : null}
      </main>
      <footer className="site-footer">
        <p>
          {dataset.publication.author} ({dataset.publication.year}).{" "}
          <a href={dataset.publication.theseus_item_url}>{dataset.publication.title}</a>. Sivuston selaaminen ei toista
          kokeita.
        </p>
        <p>
          Ajonaikainen commit {dataset.original_experiment_commit}. Tulostiedostojen commit {dataset.output_files_commit}.
          Vientiversio {dataset.website_export_revision}. Arviointi {dataset.annotations.evaluation_level}, k ={" "}
          {dataset.annotations.k}.
        </p>
      </footer>
    </>
  );
}
