# Julkaisun ja repositorion jäljitettävyys

Tämä asiakirja on johdettu tarkistusviennistä. Se ei korvaa alkuperäisiä tulostiedostoja eikä opinnäytetyötä.

- Opinnäytetyö: Karine Heinonen (2026). Hakustrategioiden vaikutus suomenkielisen RAG-järjestelmän tiedonhaun laatuun ja suorituskykyyn.
- Theseus: https://www.theseus.fi/items/4c5b8d64-c921-47f4-9c9a-52866778055a
- URN: URN:NBN:fi:amk-202604156494
- Ajonaikainen commit tallennetuissa metatiedoissa: `0bf114886e687ca706f027d81fd20bd1822b07a9`
- Commit, jossa 30 kyselyn tulostiedostot ovat puussa: `e619a3e714485ff2e6c9a833e6df317804e7e03a`
- Sivuston vientiversio: `277b83467bceb6a21960061ce32afdc210ab3fff`

Sivunumerot ovat opinnäytetyön sisällysluettelon numerointia, eivät PDF-tiedoston sivupaikkoja.

## Tilat

- **verified**: repositorion luku vastaa julkaistua taulua tai liitettä pyöristystarkkuuden puitteissa.
- **repository_only**: tieto on tallennetussa ajossa, mutta sitä ei ole julkaistu kyseisenä tauluna.
- **unresolved_prose_discrepancy**: julkaisun leipäteksti ja julkaisun oma liite sekä repositorio eroavat. Lukua ei esitetä varmennettuna.
- **excluded**: aineisto on repositoriossa, mutta sitä ei oteta päätuloksiin.

## Kuvaukset

| Tunnus | Julkaisu | Repositorio | Näkymä | Tila |
| --- | --- | --- | --- | --- |
| Taulukko 1 | 3.3, s. 17 | `documents.jsonl, chunks.jsonl, queries.jsonl, gold_annotations.jsonl` | yleiskuva | verified |
| Taulukko 2 | 5.4, s. 30 | `scripts/run_experiments.py CONFIGS` | vertailu | verified |
| Taulukko 3 | 6.2.1, s. 37 | `outputs/experiments/report_table_ablation.csv` | vertailu | verified |
| Taulukko 4 | 6.2.2, s. 38 | `outputs/experiments/report_table_latency.csv` | laatu | verified |
| Kuvio 4 | 6.2.2, s. 38–39 | `Taulukoiden 3 ja 4 nDCG@5 ja p50` | laatu | verified |
| Taulukko 5 | 6.3, s. 40 | `outputs/experiments_rerank/report_table_ablation.csv (C2–C3)` | vertailu | verified |
| Taulukko 6 | 6.3, s. 40 | `outputs/experiments_rerank/report_table_latency.csv (C2–C3)` | laatu | verified |
| Kuvio 5 | 6.3, s. 40–41 | `Taulukoiden 5 ja 6 nDCG@5 ja p50` | laatu | verified |
| Liite 3 | Liite 3, s. liite | `outputs/experiments/per_query_metrics.csv` | kysymykset | verified |
| Luku 6.4, q5 (liite 3) | 6.4, s. 42 | `outputs/experiments/per_query_metrics.csv ja liite 3` | menetelmat | verified |
| Groundedness-kooste | 5.6, s. 34 | `outputs/experiments/groundedness_summary.csv` | ei näytetä päätuloksissa | excluded_unverified_provenance |
| Aiempi 6 kyselyn tuloste | ei julkaistu taulu, s. – | `0bf114886e687ca706f027d81fd20bd1822b07a9:outputs/experiments/metrics_summary.csv` | ei näytetä | repository_history_not_publication |

## Pääablaation laatu ja latenssi

Lähde: `outputs/experiments`. Julkaisu: taulukot 3 ja 4, kuviot 4.

- `C0_baseline`: recall 0.65, nDCG 0.58, p50 26.09 ms. Laatu: verified_table_3. Latenssi: verified_table_4.
- `C1_mmr`: recall 0.7167, nDCG 0.6146, p50 26.35 ms. Laatu: verified_table_3. Latenssi: verified_table_4.
- `C2_mmr_rerank`: recall 0.7833, nDCG 0.6934, p50 258.42 ms. Laatu: verified_table_3. Latenssi: verified_table_4.
- `C3_mmr_rerank_dedupe`: recall 0.7833, nDCG 0.6934, p50 242.69 ms. Laatu: verified_table_3. Latenssi: verified_table_4.

## Uudelleenjärjestäjien vertailu

Lähde: `outputs/experiments_rerank`. Julkaistut taulukot 5 ja 6 kattavat C2- ja C3-rivit. Saman ajon C0- ja C1-latenssit ovat erillinen mittaus, eivät taulukon 4 lukuja.

## Kyselyn q5

Liite 3 ja `per_query_metrics.csv` (lähde): C0 = 1,00, C1 = 0,00, C2 = 1,00, C3 = 1,00.

Sivusto käyttää näitä lukuja. Arvot C0 = C1 = 0 ja C2 = C3 = 0,5 kuuluvat kyselylle q2.

## Aiempi tuloste samassa commit-hashissa

Ajometatiedon commitin puussa on aiempi kuuden kyselyn tuloste. Julkaistu 30 kyselyn aineisto on työpuussa ja commitissa e619a3e. Kuuden kyselyn lukuja ei piirretä tulosesittelyyn.

Kuuden kyselyn kooste kyseisessä puussa:

- `C0_baseline`: kyselyitä 6, recall 0.5833, nDCG 0.5457.
- `C1_mmr`: kyselyitä 6, recall 0.75, nDCG 0.5976.
- `C2_mmr_rerank`: kyselyitä 6, recall 0.4167, nDCG 0.4467.
- `C3_mmr_rerank_dedupe`: kyselyitä 6, recall 0.4167, nDCG 0.4467.

## Groundedness

Tiedosto sisältää C0- ja C2-rivit, mutta repositoriossa ei ole sen tuottanutta generointiajoa eikä opinnäytetyön taulukot 3–6 raportoi lukuja. Luku 5.6 käsittelee groundednessia valinnaisena lisämittarina ydinkokeen ulkopuolella. Alkuperäistä tiedostoa ei ole poistettu.

## Toistuvat dokumentit

Recall@k laskee top-k-listan yksilölliset relevantit dokumenttitunnisteet ja jakaa ne gold-joukon koolla. nDCG@k pisteyttää jokaisen sijainnin erikseen. Saman dokumentin toinen tekstikatkelma voi siis olla relevanssilistassa uusi ykkönen, eikä nDCG tiivistä dokumentteja. Diagnostinen tarkistus käyttää `scripts/run_experiments.py`-funktion `compute_recall_ndcg` -toteutusta eikä kirjoita lukuja takaisin.

## Annotaatiot

Ajometatieto ei tallentanut annotaatiotiedostojen tiivistettä. Nykyiset kysely- ja gold-tiedostot ovat samat kuin ajometatietoon kirjatun commitin puussa, mutta ajonaikaista levytilannetta ei voida todistaa jälkikäteen, jos tiedostoja olisi muutettu commitoimatta.

