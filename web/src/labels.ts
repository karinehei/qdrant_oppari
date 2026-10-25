import type { Dataset } from "./types";

export function shortConfig(dataset: Dataset, configName: string): string {
  for (const run of dataset.runs) {
    const row = run.aggregates.find((item) => item.config_name === configName);
    if (!row) {
      continue;
    }
    const code = dataset.configs[row.base_config_name]?.code ?? configName;
    if (!row.rerank_model_name) {
      return code;
    }
    if (row.rerank_model_name.includes("bge")) {
      return `${code} bge-m3`;
    }
    if (row.rerank_model_name.includes("ms-marco")) {
      return `${code} ms-marco`;
    }
    return code;
  }
  return configName;
}
