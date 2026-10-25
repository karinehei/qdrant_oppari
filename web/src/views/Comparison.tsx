import { DataTable, HorizontalBars, Legend, Panel } from "../components";
import { downloadText, fullAggregateCsv } from "../download";
import { formatFixed, formatQuality, statusLabel } from "../format";
import { shortConfig } from "../labels";
import { publishedAggregates } from "../selectors";
import type { AppState, Dataset } from "../types";

export function Comparison({
  dataset,
  state,
  onRun,
}: {
  dataset: Dataset;
  state: AppState;
  onRun: (run: string) => void;
}) {
  const rows = publishedAggregates(dataset, state.run);
  const run = dataset.runs.find((item) => item.id === state.run)!;
  const legend = rows.map((row, index) => ({ label: shortConfig(dataset, row.config_name), index }));
  return (
    <>
      <Panel title="Hakustrategioiden vertailu">
        <p>{dataset.metric_definitions.recall_fi}</p>
        <p>{dataset.metric_definitions.ndcg_fi}</p>
        <p>
          k = {dataset.metric_definitions.k}, arviointitaso: {dataset.metric_definitions.evaluation_level_fi}.{" "}
          {dataset.metric_definitions.no_significance_fi}
        </p>
        <label>
          Ajo
          <select value={state.run} onChange={(event) => onRun(event.target.value)}>
            {dataset.runs.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label_fi}
              </option>
            ))}
          </select>
        </label>
        <p>{run.measurement_context_fi}</p>
        <Legend items={legend} />
        <div className="chart-grid">
          <HorizontalBars
            title="Recall@5"
            unit=""
            rows={rows.map((row, index) => ({
              label: shortConfig(dataset, row.config_name),
              value: row.mean_recall_at_k,
              digits: 3,
              index,
            }))}
          />
          <HorizontalBars
            title="nDCG@5"
            unit=""
            rows={rows.map((row, index) => ({
              label: shortConfig(dataset, row.config_name),
              value: row.mean_ndcg_at_k,
              digits: 3,
              index,
            }))}
          />
        </div>
        <DataTable
          caption={`${run.label_fi}: julkaistu kooste. Taulun luvut eivät muutu kysymyssuodatuksesta.`}
          headers={["Konfiguraatio", "Recall@5", "nDCG@5", "Keskihajonta, recall", "Keskihajonta, nDCG", "Laadun lähde"]}
          rows={rows.map((row) => [
            shortConfig(dataset, row.config_name),
            formatQuality(row.mean_recall_at_k),
            formatQuality(row.mean_ndcg_at_k),
            formatFixed(row.std_recall_at_k, 3),
            formatFixed(row.std_ndcg_at_k, 3),
            statusLabel(row.quality_publication_status),
          ])}
        />
        <details>
          <summary>Tallennettu neljän desimaalin tarkkuus</summary>
          <DataTable
            caption="metrics_summary.csv-tiedoston keskiarvot ennen kolmen desimaalin raportointipyöristystä"
            headers={["Konfiguraatio", "Recall", "nDCG"]}
            rows={rows.map((row) => [
              row.config_name,
              String(row.underlying_mean_recall_at_k),
              String(row.underlying_mean_ndcg_at_k),
            ])}
          />
        </details>
        <p>{dataset.metric_definitions.score_fi}</p>
        <button
          type="button"
          onClick={() => {
            const file = fullAggregateCsv(dataset, state.run);
            downloadText(file.filename, file.csv);
          }}
        >
          Lataa ajon koko julkaistu kooste
        </button>
        <p className="meta">Lataus on johdettu kooste, ei alkuperäinen opinnäytetyön tiedosto.</p>
      </Panel>
    </>
  );
}
