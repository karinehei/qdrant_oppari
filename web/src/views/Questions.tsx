import { useEffect, useId, useState } from "react";
import { DataTable, Panel } from "../components";
import { downloadText, filteredQuestionCsv } from "../download";
import { categoryLabel, formatFixed, formatLatency, formatQuality } from "../format";
import { shortConfig } from "../labels";
import { configLabel, documentRankChanges, filterQuestions, findRun, hitsFor, metricFor } from "../selectors";
import type { AppState, Dataset } from "../types";

export function Questions({
  dataset,
  state,
  onChange,
}: {
  dataset: Dataset;
  state: AppState;
  onChange: (partial: Partial<AppState>, mode?: "push" | "replace") => void;
}) {
  const searchId = useId();
  const helpId = useId();
  const [draft, setDraft] = useState(state.search);
  useEffect(() => {
    setDraft(state.search);
  }, [state.search]);
  useEffect(() => {
    if (draft === state.search) {
      return undefined;
    }
    const timer = window.setTimeout(() => onChange({ search: draft }, "push"), 400);
    return () => window.clearTimeout(timer);
  }, [draft, onChange, state.search]);

  const run = findRun(dataset, state.run)!;
  const visible = filterQuestions(dataset.questions, state.search, state.category);
  const question = dataset.questions.find((item) => item.query_id === state.question) ?? visible[0];
  const leftHits = question ? hitsFor(run, question.query_id, state.left) : [];
  const rightHits = question ? hitsFor(run, question.query_id, state.right) : [];
  const leftMetric = question ? metricFor(run, question.query_id, state.left) : undefined;
  const rightMetric = question ? metricFor(run, question.query_id, state.right) : undefined;
  const changes = question ? documentRankChanges(leftHits, rightHits, question.relevant_doc_ids) : [];

  return (
    <Panel title="Kysymyskohtaiset tulokset">
      <p id={helpId}>Hakukenttä suodattaa tallennettua kysymyslistaa. Se ei käynnistä tiedonhakua eikä muuta julkaistuja keskiarvoja.</p>
      <div className="filters">
        <label htmlFor={searchId}>Suodata kysymyksiä</label>
        <input
          id={searchId}
          type="search"
          value={draft}
          aria-describedby={helpId}
          onChange={(event) => setDraft(event.target.value)}
        />
        <label>
          Luokka
          <select value={state.category} onChange={(event) => onChange({ category: event.target.value })}>
            <option value="all">Kaikki luokat</option>
            {dataset.categories.map((category) => (
              <option key={category} value={category}>
                {categoryLabel(category)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Ajo
          <select value={state.run} onChange={(event) => onChange({ run: event.target.value })}>
            {dataset.runs.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label_fi}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p role="status">
        {visible.length} tallennettua kysymystä näkyy. Julkaistu kooste kattaa edelleen {run.provenance.query_count} kyselyä.
      </p>
      {visible.length === 0 ? (
        <p className="empty">Yksikään tallennettu kysymys ei vastaa suodatusta.</p>
      ) : (
        <div className="question-layout">
          <ul className="question-list">
            {visible.map((item) => (
              <li key={item.query_id}>
                <button
                  type="button"
                  aria-pressed={question?.query_id === item.query_id}
                  onClick={() => onChange({ question: item.query_id })}
                >
                  <span>{item.query_id}</span>
                  {item.query_text}
                </button>
              </li>
            ))}
          </ul>
          {question ? (
            <div>
              <h3>
                {question.query_id}. {question.query_text}
              </h3>
              <p>
                Luokka: {categoryLabel(question.category)}. Relevantiksi merkityt dokumentit:{" "}
                {question.relevant_doc_ids.join(", ") || "ei yhtään"}.
              </p>
              <p>{dataset.annotations.identity.uncertainty_fi}</p>
              <div className="pair">
                <ConfigSelect
                  label="Vasen konfiguraatio"
                  value={state.left}
                  configs={run.aggregates.map((row) => row.config_name)}
                  dataset={dataset}
                  onChange={(left) => onChange({ left })}
                />
                <ConfigSelect
                  label="Oikea konfiguraatio"
                  value={state.right}
                  configs={run.aggregates.map((row) => row.config_name)}
                  dataset={dataset}
                  onChange={(right) => onChange({ right })}
                />
              </div>
              <DataTable
                caption="Tallennetut kyselykohtaiset mittarit. Arviointi on dokumenttitasoista."
                headers={["Konfiguraatio", "Recall@5", "nDCG@5", "Latenssi"]}
                rows={[leftMetric, rightMetric].filter(Boolean).map((metric) => [
                  shortConfig(dataset, metric!.config_name),
                  formatQuality(metric!.recall_at_k),
                  formatQuality(metric!.ndcg_at_k),
                  formatLatency(metric!.latency_ms),
                ])}
              />
              <div className="compare">
                <HitColumn title={configLabel(dataset, state.left)} hits={leftHits} relevant={question.relevant_doc_ids} absence={dataset.annotations.absence_label_fi} />
                <HitColumn title={configLabel(dataset, state.right)} hits={rightHits} relevant={question.relevant_doc_ids} absence={dataset.annotations.absence_label_fi} />
              </div>
              <h3>Dokumenttien sijamuutokset</h3>
              <p>Sija on dokumentin ensimmäinen esiintymä. Tekstikatkelmia näytetään erikseen, mutta arviointi pysyy dokumenttitasolla.</p>
              {changes.length === 0 ? (
                <p className="empty">Dokumenttien ensimmäiset sijat eivät muutu näiden konfiguraatioiden välillä.</p>
              ) : (
                <DataTable
                  caption="Muuttuneet dokumenttisijat"
                  headers={["Dokumentti", "Vasen sija", "Oikea sija", "Muutos", "Arvio"]}
                  rows={changes.map((change) => [
                    change.docId,
                    change.leftRank ? String(change.leftRank) : "–",
                    change.rightRank ? String(change.rightRank) : "–",
                    change.direction,
                    change.relevant ? "Merkitty relevantiksi" : dataset.annotations.absence_label_fi,
                  ])}
                />
              )}
              <button
                type="button"
                onClick={() => {
                  const file = filteredQuestionCsv(dataset, state.run, visible);
                  downloadText(file.filename, file.csv);
                }}
              >
                Lataa suodatettu kysymyslista
              </button>
              <p className="meta">Suodatettu lataus ei ole koko julkaistu koe.</p>
            </div>
          ) : null}
        </div>
      )}
    </Panel>
  );
}

function ConfigSelect({
  label,
  value,
  configs,
  dataset,
  onChange,
}: {
  label: string;
  value: string;
  configs: string[];
  dataset: Dataset;
  onChange: (value: string) => void;
}) {
  return (
    <label>
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {configs.map((config) => (
          <option key={config} value={config}>
            {configLabel(dataset, config)}
          </option>
        ))}
      </select>
    </label>
  );
}

function HitColumn({
  title,
  hits,
  relevant,
  absence,
}: {
  title: string;
  hits: { rank: number; doc_id: string; chunk_id: string; uid: string | null; retrieval_score: number | null; rerank_score: number | null }[];
  relevant: string[];
  absence: string;
}) {
  return (
    <section className="hit-column">
      <h3>{title}</h3>
      {hits.length === 0 ? <p className="empty">Tälle kyselylle ei ole tallennettuja osumia.</p> : null}
      <ol>
        {hits.map((hit) => (
          <li key={`${hit.rank}-${hit.chunk_id}`}>
            <p>
              <strong>Sija {hit.rank}.</strong> Dokumentti {hit.doc_id}. Katkelma {hit.chunk_id}.
            </p>
            <p>{relevant.includes(hit.doc_id) ? "Merkitty relevantiksi" : absence}</p>
            <p>Vektorihaku: {hit.retrieval_score === null ? "–" : formatFixed(hit.retrieval_score, 3)}</p>
            <p>Uudelleenjärjestäjä: {hit.rerank_score === null ? "–" : formatFixed(hit.rerank_score, 3)}</p>
            <p className="meta">Uid: {hit.uid ?? "–"}. Pisteitä ei verrata mallien välillä eikä lueta prosentteina.</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
