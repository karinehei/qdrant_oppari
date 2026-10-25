import { DataTable, HorizontalBars, Legend, Panel, ScatterPlot } from "../components";
import { formatLatency, formatQuality, statusLabel } from "../format";
import { shortConfig } from "../labels";
import { publishedAggregates } from "../selectors";
import type { AppState, Dataset, MetricId } from "../types";

const METRICS: { id: MetricId; label: string }[] = [
  { id: "recall", label: "Recall@5" },
  { id: "ndcg", label: "nDCG@5" },
  { id: "p50", label: "p50-latenssi" },
  { id: "p95", label: "p95-latenssi" },
  { id: "p99", label: "p99-latenssi" },
];

function metricValue(id: MetricId, row: ReturnType<typeof publishedAggregates>[number]): number {
  if (id === "recall") return row.mean_recall_at_k;
  if (id === "ndcg") return row.mean_ndcg_at_k;
  if (id === "p50") return row.p50_latency_ms;
  if (id === "p95") return row.p95_latency_ms;
  return row.p99_latency_ms;
}

export function Quality({
  dataset,
  state,
  onChange,
}: {
  dataset: Dataset;
  state: AppState;
  onChange: (partial: Partial<AppState>) => void;
}) {
  const rows = publishedAggregates(dataset, state.run);
  const run = dataset.runs.find((item) => item.id === state.run)!;
  const digits = state.metric === "recall" || state.metric === "ndcg" ? 3 : 2;
  const legend = rows.map((row, index) => ({ label: shortConfig(dataset, row.config_name), index }));
  return (
    <Panel title="Laatu ja viive">
      <p>{dataset.metric_definitions.latency_fi}</p>
      <p>{run.measurement_context_fi}</p>
      <p>
        Laitteisto: {run.provenance.environment.gpu_device_name ?? "ei tallennettua GPU-tietoa"}. Kesto{" "}
        {run.provenance.duration_seconds} s. {dataset.metric_definitions.no_significance_fi}
      </p>
      <div className="filters">
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
        <label>
          Mittari
          <select value={state.metric} onChange={(event) => onChange({ metric: event.target.value as MetricId })}>
            {METRICS.map((metric) => (
              <option key={metric.id} value={metric.id}>
                {metric.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Legend items={legend} />
      <HorizontalBars
        title={METRICS.find((metric) => metric.id === state.metric)?.label ?? "Mittari"}
        unit={digits === 2 ? "ms" : ""}
        rows={rows.map((row, index) => ({
          label: shortConfig(dataset, row.config_name),
          value: metricValue(state.metric, row),
          digits,
          index,
        }))}
      />
      <ScatterPlot
        title="nDCG@5 ja p50-latenssi samassa ajossa"
        points={rows.map((row, index) => ({
          label: shortConfig(dataset, row.config_name),
          x: row.p50_latency_ms,
          y: row.mean_ndcg_at_k,
          index,
        }))}
      />
      <DataTable
        caption={`${run.label_fi}: laatu ja latenssi. Yksiköt ovat mittarin oma asteikko ja millisekunnit.`}
        headers={["Konfiguraatio", "Recall@5", "nDCG@5", "p50", "p95", "p99", "Latenssin lähde"]}
        rows={rows.map((row) => [
          shortConfig(dataset, row.config_name),
          formatQuality(row.mean_recall_at_k),
          formatQuality(row.mean_ndcg_at_k),
          formatLatency(row.p50_latency_ms),
          formatLatency(row.p95_latency_ms),
          formatLatency(row.p99_latency_ms),
          statusLabel(row.latency_publication_status),
        ])}
      />
      <h3>Mitä eroista voi sanoa</h3>
      <ul>
        {dataset.conclusions.map((item) => (
          <li key={item.text_fi}>{item.text_fi}</li>
        ))}
      </ul>
    </Panel>
  );
}
