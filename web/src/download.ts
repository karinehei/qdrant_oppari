import { publishedAggregates } from "./selectors";
import type { Dataset, Question } from "./types";

function csvEscape(value: string | number): string {
  const text = String(value);
  if (/[",\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

export function fullAggregateCsv(dataset: Dataset, runId: string): { filename: string; csv: string; label: string } {
  const run = dataset.runs.find((item) => item.id === runId);
  if (!run) {
    throw new Error("Tuntematon ajo");
  }
  const header = [
    "record_type",
    "note",
    "run_id",
    "eval_level",
    "k",
    "unit",
    "source_dir",
    "experiment_commit",
    "output_files_commit",
    "website_export_revision",
    "config_name",
    "query_count",
    "mean_recall_at_k",
    "mean_ndcg_at_k",
    "p50_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "quality_publication_status",
    "latency_publication_status",
  ];
  const provenance = run.provenance;
  const rows = [
    header.join(","),
    [
      "metadata",
      "Johdettu vientitiedosto. Ei alkuperäinen opinnäytetyön tiedosto. Kysymyssuodatus ei sisälly tähän koosteeseen.",
      run.id,
      provenance.eval_level,
      provenance.top_k,
      "recall_ndcg_unitless_and_latency_ms",
      provenance.source_dir,
      provenance.runtime_git_commit,
      provenance.output_files_commit,
      dataset.website_export_revision,
      "",
      provenance.query_count,
      "",
      "",
      "",
      "",
      "",
      "",
      "",
    ].map(csvEscape).join(","),
    ...publishedAggregates(dataset, runId).map((row) =>
      [
        "aggregate",
        "Koko julkaistu ajo",
        run.id,
        provenance.eval_level,
        provenance.top_k,
        "recall_ndcg_unitless_and_latency_ms",
        provenance.source_dir,
        provenance.runtime_git_commit,
        provenance.output_files_commit,
        dataset.website_export_revision,
        row.config_name,
        row.query_count,
        row.mean_recall_at_k,
        row.mean_ndcg_at_k,
        row.p50_latency_ms,
        row.p95_latency_ms,
        row.p99_latency_ms,
        row.quality_publication_status,
        row.latency_publication_status,
      ].map(csvEscape).join(","),
    ),
  ];
  return {
    filename: `${run.id}_julkaistu_kooste.csv`,
    csv: `${rows.join("\n")}\n`,
    label: "Lataa ajon koko julkaistu kooste",
  };
}

export function filteredQuestionCsv(
  dataset: Dataset,
  runId: string,
  questions: Question[],
): { filename: string; csv: string; label: string } {
  const run = dataset.runs.find((item) => item.id === runId);
  if (!run) {
    throw new Error("Tuntematon ajo");
  }
  const header = [
    "record_type",
    "note",
    "run_id",
    "eval_level",
    "k",
    "query_id",
    "category",
    "config_name",
    "recall_at_k",
    "ndcg_at_k",
    "latency_ms",
  ];
  const lines = [
    header.join(","),
    [
      "metadata",
      "Suodatettu kysymyslista. Tämä ei ole julkaistu kooste eikä muuta taulukoiden keskiarvoja.",
      run.id,
      run.provenance.eval_level,
      run.provenance.top_k,
      "",
      "",
      "",
      "",
      "",
      "",
    ].map(csvEscape).join(","),
  ];
  for (const question of questions) {
    for (const metric of run.per_query.filter((row) => row.query_id === question.query_id)) {
      lines.push(
        [
          "filtered_question",
          "Suodatettu rivi, ei koko kokeen keskiarvo",
          run.id,
          run.provenance.eval_level,
          run.provenance.top_k,
          question.query_id,
          question.category,
          metric.config_name,
          metric.recall_at_k,
          metric.ndcg_at_k,
          metric.latency_ms,
        ].map(csvEscape).join(","),
      );
    }
  }
  return {
    filename: `${run.id}_suodatettu_kysymyslista.csv`,
    csv: `${lines.join("\n")}\n`,
    label: "Lataa suodatettu kysymyslista",
  };
}

export function downloadText(filename: string, contents: string): void {
  const blob = new Blob([contents], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
