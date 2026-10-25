import { DataTable, Panel } from "../components";
import { statusLabel } from "../format";
import type { Dataset } from "../types";

export function Methods({ dataset }: { dataset: Dataset }) {
  return (
    <>
      <Panel title="Menetelmät">
        <p>{dataset.metric_definitions.recall_fi}</p>
        <p>{dataset.metric_definitions.ndcg_fi}</p>
        <p>{dataset.metric_definitions.latency_fi}</p>
        <p>{dataset.metric_definitions.score_fi}</p>
        <p>
          Luvuissa 2 ja 5.4 recall@k on relevanttien dokumenttien osuus. Luvun 6.1 yksittäinen virke kuvaa mittaria
          suppeammin (“vähintään yksi”). Taulukoiden luvut vastaavat osuuteen perustuvaa laskentaa, ja sivusto käyttää
          sitä.
        </p>
        <p>{dataset.annotations.identity.uncertainty_fi}</p>
      </Panel>
      <Panel title="Tapausesimerkit">
        <p>
          Esimerkit sisältävät parannuksia, ennallaan pysyneitä tuloksia ja kompromisseja. q5:n leipätekstin virkettä ei
          esitetä varmennettuna.
        </p>
        {dataset.case_studies.map((item) => (
          <article key={`${item.kind}-${item.query_id ?? "aggregate"}`} className="case">
            <h3>
              {item.query_id ? `Kysely ${item.query_id}` : "C2 ja C3"}{" "}
              <span className={item.show_as_thesis_verified ? "badge ok" : "badge warn"}>
                {statusLabel(item.publication_status)}
              </span>
            </h3>
            <p>{item.summary_fi}</p>
            {item.reference ? (
              <p className="meta">
                {item.reference.section ? `Luku ${item.reference.section}` : ""}
                {item.reference.page ? `, s. ${item.reference.page}` : ""}
                {item.reference.appendix ? `, ${item.reference.appendix}` : ""}
                {item.reference.table ? `, ${item.reference.table}` : ""}
              </p>
            ) : null}
          </article>
        ))}
      </Panel>
      <Panel title="Rajoitukset">
        <ul>
          {dataset.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <h3>Groundedness</h3>
        <p>{dataset.groundedness.reason_fi}</p>
      </Panel>
      <Panel title="Jäljitettävyys">
        <p>{dataset.publication.page_basis_fi}</p>
        <DataTable
          caption="Julkaisun kohdat, repositorion tiedostot ja sivuston näkymät"
          headers={["Julkaisu", "Repositorio", "Näkymä", "Tila"]}
          rows={dataset.traceability.map((row) => [row.label_fi, row.repository, row.website_view, row.status])}
        />
        <ul>
          {dataset.runs.flatMap((run) =>
            run.provenance.files
              .filter((file) => file.github_url)
              .map((file) => (
                <li key={file.path}>
                  <a href={file.github_url ?? "#"}>{file.path}</a>
                </li>
              )),
          )}
        </ul>
      </Panel>
    </>
  );
}
