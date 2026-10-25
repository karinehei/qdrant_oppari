export interface DocumentRecord {
  doc_id: string;
  author: string | null;
  filename_derived_label: string | null;
  year: number | null;
  theseus_url: string | null;
  language: string | null;
  chunk_count: number;
  cleaned_text_length: number;
  bibliographic_status: string;
  bibliographic_note_fi: string;
}

export interface Question {
  query_id: string;
  query_text: string;
  category: string;
  language: string;
  relevant_doc_ids: string[];
  relevant_chunk_ids: string[];
  notes: string;
  negative_judgments: boolean;
}

export interface ConfigDefinition {
  code: string;
  order: number;
  label_fi: string;
  mmr: boolean;
  diversity: number;
  rerank: boolean;
  dedupe: boolean;
  description_fi: string;
  dedupe_rule_fi?: string;
}

export interface Aggregate {
  config_name: string;
  base_config_name: string;
  rerank_model_name: string | null;
  query_count: number;
  mean_recall_at_k: number;
  mean_ndcg_at_k: number;
  std_recall_at_k: number;
  std_ndcg_at_k: number;
  underlying_mean_recall_at_k: number;
  underlying_mean_ndcg_at_k: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  quality_publication_status: string;
  latency_publication_status: string;
  publication_reference_ids: string[];
}

export interface PerQueryMetric {
  query_id: string;
  config_name: string;
  base_config_name: string;
  rerank_model_name: string | null;
  recall_at_k: number;
  ndcg_at_k: number;
  latency_ms: number;
  status: string;
}

export interface Hit {
  query_id: string;
  config_name: string;
  rank: number;
  doc_id: string;
  chunk_id: string;
  uid: string | null;
  retrieval_score: number | null;
  rerank_score: number | null;
}

export interface RunFile {
  path: string;
  present_in_runtime_commit: boolean;
  working_tree_matches_runtime_commit: boolean | null;
  present_in_output_commit: boolean;
  working_tree_matches_output_commit: boolean | null;
  github_url: string | null;
}

export interface Run {
  id: string;
  label_fi: string;
  measurement_context_fi: string;
  provenance: {
    source_dir: string;
    timestamp_utc: string;
    seed: number;
    runtime_git_commit: string;
    output_files_commit: string;
    collection_name: string;
    top_k: number;
    initial_limit: number;
    score_threshold: number;
    eval_level: string;
    query_count: number;
    duration_seconds: number;
    rerank_models_loaded: string[];
    embedding_model: string;
    environment: {
      python_version: string;
      platform: string;
      gpu_device_name: string | null;
      package_versions: Record<string, string | null>;
    };
    files: RunFile[];
    omitted_fi: string;
  };
  aggregates: Aggregate[];
  per_query: PerQueryMetric[];
  hits: Hit[];
}

export interface CaseStudy {
  query_id: string | null;
  kind: string;
  publication_status: string;
  show_as_thesis_verified: boolean;
  summary_fi: string;
  reference?: { section?: string; page?: string; appendix?: string; table?: string };
  metrics?: Record<string, { recall: number; ndcg: number; latency_ms: number }>;
}

export interface TraceRow {
  id: string;
  label_fi: string;
  section: string;
  page: string;
  repository: string;
  website_view: string;
  status: string;
}

export interface Dataset {
  schema_version: string;
  generated_at_utc: string;
  website_export_revision: string;
  original_experiment_commit: string;
  output_files_commit: string;
  boundary: { title_fi: string; statement_fi: string };
  publication: {
    title: string;
    author: string;
    year: number;
    page_count: number;
    institution: string;
    degree: string;
    theseus_item_url: string;
    theseus_handle_url: string;
    urn: string;
    page_basis_fi: string;
  };
  purpose_fi: string;
  corpus: Record<string, number>;
  documents: DocumentRecord[];
  categories: string[];
  questions: Question[];
  annotations: {
    evaluation_level: string;
    k: number;
    negative_judgments_present: boolean;
    absence_label_fi: string;
    identity: { uncertainty_fi: string };
  };
  configs: Record<string, ConfigDefinition>;
  models: {
    embedding: string;
    embedding_dimension: number;
    distance: string;
    collection_name: string;
    default_reranker: string;
    comparison_reranker: string;
    initial_limit: number;
    top_k: number;
    score_threshold: number;
    seed: number;
  };
  metric_definitions: {
    k: number;
    evaluation_level_fi: string;
    recall_fi: string;
    ndcg_fi: string;
    latency_fi: string;
    score_fi: string;
    no_significance_fi: string;
  };
  runs: Run[];
  case_studies: CaseStudy[];
  groundedness: { included_in_main_results: boolean; reason_fi: string };
  conclusions: { text_fi: string; references: string[]; status: string }[];
  limitations: string[];
  traceability: TraceRow[];
  validation: {
    release_blocked: boolean;
    release_block_reason_fi: string;
    material_discrepancies: { code: string; message: string }[];
  };
}

export type RouteId = "yleiskuva" | "vertailu" | "kysymykset" | "laatu" | "menetelmat";
export type MetricId = "recall" | "ndcg" | "p50" | "p95" | "p99";

export interface AppState {
  route: RouteId;
  run: string;
  question: string;
  left: string;
  right: string;
  category: string;
  search: string;
  metric: MetricId;
  notices: string[];
}
