import { findRun } from "./selectors";
import type { AppState, Dataset, MetricId, RouteId } from "./types";

export const ROUTES: RouteId[] = ["yleiskuva", "vertailu", "kysymykset", "laatu", "menetelmat"];
const METRICS: MetricId[] = ["recall", "ndcg", "p50", "p95", "p99"];

export function defaultState(dataset: Dataset): AppState {
  const run = dataset.runs[0];
  return {
    route: "yleiskuva",
    run: run.id,
    question: dataset.questions[0]?.query_id ?? "",
    left: run.aggregates[0]?.config_name ?? "",
    right: run.aggregates[Math.min(2, run.aggregates.length - 1)]?.config_name ?? "",
    category: "all",
    search: "",
    metric: "ndcg",
    notices: [],
  };
}

function configsFor(dataset: Dataset, runId: string): string[] {
  return findRun(dataset, runId)?.aggregates.map((row) => row.config_name) ?? [];
}

export function parseHash(hash: string, dataset: Dataset): AppState {
  const fallback = defaultState(dataset);
  const notices: string[] = [];
  const raw = hash.startsWith("#") ? hash.slice(1) : hash;
  const [pathPart = "", queryPart = ""] = raw.split("?");
  const routeName = decodeURIComponent(pathPart.replace(/^\/+/, ""));
  let route = fallback.route;
  if (routeName && ROUTES.includes(routeName as RouteId)) {
    route = routeName as RouteId;
  } else if (routeName) {
    notices.push("Osoitteen näkymää ei tunnistettu. Näytetään yleiskuva.");
  }

  const params = new URLSearchParams(queryPart);
  let run = params.get("run") || fallback.run;
  if (!findRun(dataset, run)) {
    notices.push("Ajoa ei löydy tallennetuista kokeista. Näytetään pääablaatio.");
    run = fallback.run;
  }
  const configs = configsFor(dataset, run);
  let left = params.get("left") || configs[0] || "";
  let right = params.get("right") || configs[Math.min(2, configs.length - 1)] || "";
  if (!configs.includes(left) || !configs.includes(right)) {
    notices.push("Konfiguraatio ei kuulu valittuun ajoon. Valinta palautettiin ajon omiin konfiguraatioihin.");
    left = configs[0] ?? "";
    right = configs[Math.min(2, configs.length - 1)] ?? "";
  }
  if (left && left === right && configs.length > 1) {
    notices.push("Vertailuun tarvitaan kaksi eri konfiguraatiota.");
    right = configs.find((name) => name !== left) ?? right;
  }

  let question = params.get("q") || fallback.question;
  if (!dataset.questions.some((item) => item.query_id === question)) {
    notices.push("Kyselytunnistetta ei ole tallennetussa kysymysjoukossa.");
    question = fallback.question;
  }
  let category = params.get("category") || "all";
  if (category !== "all" && !dataset.categories.includes(category)) {
    notices.push("Kysymysluokkaa ei löydy. Suodatus näyttää kaikki luokat.");
    category = "all";
  }
  let search = params.get("search") || "";
  if (search.length > 200) {
    notices.push("Hakuteksti lyhennettiin 200 merkkiin. Suodatus ei käynnistä tiedonhakua.");
    search = search.slice(0, 200);
  }
  let metric = (params.get("metric") || "ndcg") as MetricId;
  if (!METRICS.includes(metric)) {
    notices.push("Mittaria ei ole tässä kokeessa. Näytetään nDCG@5.");
    metric = "ndcg";
  }

  return { route, run, question, left, right, category, search, metric, notices };
}

export function serializeHash(state: AppState, dataset: Dataset): string {
  const defaults = defaultState(dataset);
  const params = new URLSearchParams();
  if (state.run !== defaults.run) {
    params.set("run", state.run);
  }
  if (state.question !== defaults.question) {
    params.set("q", state.question);
  }
  if (state.left !== defaults.left) {
    params.set("left", state.left);
  }
  if (state.right !== defaults.right) {
    params.set("right", state.right);
  }
  if (state.category !== "all") {
    params.set("category", state.category);
  }
  if (state.search) {
    params.set("search", state.search);
  }
  if (state.metric !== "ndcg") {
    params.set("metric", state.metric);
  }
  const query = params.toString();
  return `#/${state.route}${query ? `?${query}` : ""}`;
}
