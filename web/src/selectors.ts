import type { Aggregate, Dataset, Hit, Question, Run } from "./types";

export function configLabel(dataset: Dataset, configName: string): string {
  for (const run of dataset.runs) {
    const row = run.aggregates.find((item) => item.config_name === configName);
    if (!row) {
      continue;
    }
    const base = dataset.configs[row.base_config_name];
    const prefix = `${base.code} ${base.label_fi}`;
    return row.rerank_model_name ? `${prefix} · ${row.rerank_model_name}` : prefix;
  }
  return configName;
}

export function publishedAggregates(dataset: Dataset, runId: string): Aggregate[] {
  const run = dataset.runs.find((item) => item.id === runId);
  if (!run) {
    throw new Error(`Tuntematon ajo: ${runId}`);
  }
  return run.aggregates;
}

export function findRun(dataset: Dataset, runId: string): Run | undefined {
  return dataset.runs.find((item) => item.id === runId);
}

export function filterQuestions(questions: Question[], search: string, category: string): Question[] {
  const needle = search.trim().toLocaleLowerCase("fi");
  return questions.filter((question) => {
    if (category !== "all" && question.category !== category) {
      return false;
    }
    if (!needle) {
      return true;
    }
    const haystack = `${question.query_id} ${question.query_text} ${question.category}`.toLocaleLowerCase("fi");
    return haystack.includes(needle);
  });
}

export function hitsFor(run: Run, queryId: string, configName: string): Hit[] {
  return run.hits
    .filter((hit) => hit.query_id === queryId && hit.config_name === configName)
    .sort((left, right) => left.rank - right.rank);
}

export function metricFor(run: Run, queryId: string, configName: string) {
  return run.per_query.find((row) => row.query_id === queryId && row.config_name === configName);
}

export interface RankChange {
  docId: string;
  leftRank: number | null;
  rightRank: number | null;
  direction: "nousi" | "laski" | "ilmestyi" | "poistui" | "ennallaan";
  relevant: boolean;
}

function firstRanks(hits: Hit[]): Map<string, number> {
  const ranks = new Map<string, number>();
  for (const hit of hits) {
    if (!ranks.has(hit.doc_id)) {
      ranks.set(hit.doc_id, hit.rank);
    }
  }
  return ranks;
}

export function documentRankChanges(leftHits: Hit[], rightHits: Hit[], relevantIds: string[]): RankChange[] {
  const left = firstRanks(leftHits);
  const right = firstRanks(rightHits);
  const ids = [...new Set([...left.keys(), ...right.keys()])];
  return ids
    .map((docId) => {
      const leftRank = left.get(docId) ?? null;
      const rightRank = right.get(docId) ?? null;
      let direction: RankChange["direction"] = "ennallaan";
      if (leftRank === null && rightRank !== null) {
        direction = "ilmestyi";
      } else if (leftRank !== null && rightRank === null) {
        direction = "poistui";
      } else if (leftRank !== null && rightRank !== null && rightRank < leftRank) {
        direction = "nousi";
      } else if (leftRank !== null && rightRank !== null && rightRank > leftRank) {
        direction = "laski";
      }
      return {
        docId,
        leftRank,
        rightRank,
        direction,
        relevant: relevantIds.includes(docId),
      };
    })
    .filter((change) => change.direction !== "ennallaan");
}
