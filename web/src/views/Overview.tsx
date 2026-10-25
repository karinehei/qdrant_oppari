import { DataTable, Panel } from "../components";
import { categoryLabel, formatLatency, formatQuality, shortHash } from "../format";
import { publishedAggregates } from "../selectors";
import type { Dataset } from "../types";

export function Overview({ dataset }: { dataset: Dataset }) {
  const publication = dataset.publication;
  const corpus = dataset.corpus;
  const ablation = publishedAggregates(dataset, "ablation");
  const counts = dataset.questions.reduce<Record<string, number>>((accumulator, question) => {
    accumulator[question.category] = (accumulator[question.category] ?? 0) + 1;
    return accumulator;
  }, {});
  return (
    <>
      <Panel title="Julkaisu">
        <p className="lead">{publication.title}</p>
        <p>
          {publication.author}, {publication.year}. {publication.degree}, {publication.institution}.{" "}
          {publication.page_count} sivua.
        </p>
        <p>{dataset.purpose_fi}</p>
        <p>
          <a href={publication.theseus_item_url}>Theseus-tietue</a>
          {" · "}
          <a href={publication.theseus_handle_url}>Handle</a>
          {" · "}
          <span>{publication.urn}</span>
        </p>
      </Panel>
      <Panel title="Kokeen laajuus">
        <DataTable
          caption="Aineiston laajuus, taulukko 1"
          headers={["Osa", "Arvo"]}
          rows={[
            ["Dokumentteja", String(corpus.document_count)],
            ["Tekstikatkelmia", String(corpus.chunk_count)],
            ["Kyselyitä ja gold-annotaatioita", `${corpus.query_count} / ${corpus.gold_count}`],
            ["Arviointitaso ja k", `${dataset.annotations.evaluation_level}, k = ${dataset.annotations.k}`],
            ["Upotemalli", dataset.models.embedding],
            ["Kokoelma ja etäisyys", `${dataset.models.collection_name}, ${dataset.models.distance}`],
            ["Ehdokasraja ja kynnys", `${dataset.models.initial_limit}, ${dataset.models.score_threshold}`],
            ["Siemen", String(dataset.models.seed)],
          ]}
        />
        <DataTable
          caption="Kysymysten luokat"
          headers={["Luokka", "Kyselyitä"]}
          rows={Object.entries(counts).map(([category, count]) => [categoryLabel(category), String(count)])}
        />
      </Panel>
      <Panel title="Konfiguraatiot C0–C3">
        <ol className="steps">
          {Object.values(dataset.configs)
            .sort((left, right) => left.order - right.order)
            .map((config) => (
              <li key={config.code}>
                <strong>
                  {config.code} {config.label_fi}
                </strong>
                <p>{config.description_fi}</p>
              </li>
            ))}
        </ol>
        <p>
          Pääablaation uudelleenjärjestäjä on {dataset.models.default_reranker}. Erillisessä vertailussa mukana on myös{" "}
          {dataset.models.comparison_reranker}. Ajot pidetään erillään, koska niiden latenssit on mitattu eri kerroilla.
        </p>
      </Panel>
      <Panel title="Pääablaation kooste">
        <p>
          Luvut ovat taulukoiden 3 ja 4 julkaistuja koosteita, k = 5, dokumenttitaso, n = 30. C2 ja C3 jakavat saman
          keskimääräisen laadun. Taulun automaattinen “paras konfiguraatio” nimeää C2:n vain järjestyssyistä.
        </p>
        <DataTable
          caption="Pääablaation recall@5, nDCG@5 ja p50"
          headers={["Konfiguraatio", "Recall@5", "nDCG@5", "p50"]}
          rows={ablation.map((row) => [
            dataset.configs[row.base_config_name].label_fi,
            formatQuality(row.mean_recall_at_k),
            formatQuality(row.mean_ndcg_at_k),
            formatLatency(row.p50_latency_ms),
          ])}
        />
        <p className="meta">
          Ajonaikainen commit {shortHash(dataset.original_experiment_commit)}. Tulostiedostot commitissa{" "}
          {shortHash(dataset.output_files_commit)}. Vientiversio {shortHash(dataset.website_export_revision)}.
        </p>
      </Panel>
    </>
  );
}
