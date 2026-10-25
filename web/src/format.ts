const CATEGORY_LABELS: Record<string, string> = {
  RAG_perusteet: "RAG-perusteet",
  tekniikka: "Tekniikka",
  toteutus: "Toteutus",
  LLM: "LLM",
  sovellus: "Sovellus",
};

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

export function formatQuality(value: number): string {
  const fixed = value.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  const [whole, fraction = ""] = fixed.split(".");
  const padded = fraction.padEnd(2, "0");
  return `${groupThousands(whole)},${padded}`;
}

export function formatFixed(value: number, digits: number): string {
  const [whole, fraction] = value.toFixed(digits).split(".");
  return `${groupThousands(whole)},${fraction}`;
}

export function formatLatency(value: number): string {
  return `${formatFixed(value, 2)} ms`;
}

function groupThousands(whole: string): string {
  const sign = whole.startsWith("-") ? "-" : "";
  const digits = sign ? whole.slice(1) : whole;
  return sign + digits.replace(/\B(?=(\d{3})+(?!\d))/g, "\u00a0");
}

export function shortHash(value: string): string {
  return value.slice(0, 7);
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    verified: "Varmennettu julkaisuun",
    verified_table_3: "Taulukko 3",
    verified_table_4: "Taulukko 4",
    verified_table_5: "Taulukko 5",
    verified_table_6: "Taulukko 6",
    verified_partial: "Recall varmennettu, nDCG täydentää tallenteesta",
    verified_with_rounding: "Varmennettu pyöristyksellä",
    unverified_prose_discrepancy: "Leipätekstin virkettä ei ole varmennettu",
    repository_only_separate_run: "Vain repositorio, erillinen ajo",
  };
  return labels[status] ?? status;
}
