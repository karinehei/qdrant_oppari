# Retrieval Case Studies

*Generated: 2026-02-27 10:30 UTC*

## Run Metadata

- **collection_name:** rag_thesis_fi
- **top_k:** 5
- **initial_limit:** 20
- **score_threshold:** 0.0
- **eval_level:** doc
- **seed:** 42
- **rerank_models_loaded:** ['BAAI/bge-reranker-v2-m3']

This appendix shows concrete retrieval examples: question, retrieved sources, metrics, and brief interpretation. Cases include best- and worst-performing queries, latency outliers, and config disagreements.

## Case 1 — q6

**Question:** Miten cross-encoder parantaa hakutulosten relevanssia?

**Gold (relevant_doc_ids):** Antikainen_Jari

**Focus config:** C2_mmr_rerank

**Metrics (focus config):** recall@k=1.0000, nDCG@k=1.0000, latency_ms=1141.8

### Top hits (focus config, top K)

| rank | doc_id | title | score | rerank_score | snippet |
| --- | --- | --- | --- | --- | --- |
| 1 | Antikainen_Jari | Antikainen Jari | 0.685 | 0.919 | 2. Uudelleenjärjestäminen (Re-ranking): Cross-encoder-pohjainen uudell… |
| 2 | Antikainen_Jari | Antikainen Jari | 0.648 | 0.900 | (esim. hybridi- tai monikyselyhakija) hakee laajemman joukon dokumentt… |
| 3 | Sarkiniemi_Mikko | Sarkiniemi Mikko | 0.686 | 0.041 | sisältöihin. Tämä parantaa hakutulosten relevanssia ja RAG-mallin tuot… |
| 4 | Martin_Joel | Martin Joel | 0.698 | 0.015 | muotoon. Myös kysymysten esikäsittely voi parantaa tuloksia muotoilema… |
| 5 | Sarkiniemi_Mikko | Sarkiniemi Mikko | 0.632 | 0.013 | mahdollistaa tarkemmat ja relevantimmat hakutulokset. Nämä auttavat LL… |

### Comparison (all configs)

| config_name | recall@k | nDCG@k | latency_ms |
| --- | --- | --- | --- |
| C0_baseline | 1.0000 | 0.5438 | 35.8 |
| C1_mmr | 1.0000 | 0.5438 | 34.5 |
| C2_mmr_rerank | 1.0000 | 1.0000 | 1141.8 |
| C3_mmr_rerank_dedupe | 1.0000 | 1.0000 | 1140.6 |

### Interpretation

- **Success:** All gold documents/chunks were retrieved in top-k.
- Gold was ranked highly (nDCG@k ≥ 0.9).

---

## Case 2 — q24

**Question:** Miten vektoritietokanta eroaa perinteisestä tietokannasta?

**Gold (relevant_doc_ids):** Antikainen_Jari, Holopainen_Petri

**Focus config:** C2_mmr_rerank

**Metrics (focus config):** recall@k=0.0000, nDCG@k=0.0000, latency_ms=267.9

### Top hits (focus config, top K)

| rank | doc_id | title | score | rerank_score | snippet |
| --- | --- | --- | --- | --- | --- |
| 1 | Pulli_Samu | Pulli Samu | 0.782 | 0.993 | 3.2.2 Vektoritietokannat Vektoritietokanta on kokoelma numeroilla esit… |
| 2 | Majander_Pyry | Majander Pyry | 0.649 | 0.548 | Kuva 9. Sanojen vektoriesitykset euklidisessa avaruudessa (mukaillen K… |
| 3 | Martin_Joel | Martin Joel | 0.719 | 0.442 | käyttötarkoituksiin. [27.] Toisin sanoen vektoritietokannat toimivat s… |
| 4 | Majander_Pyry | Majander Pyry | 0.716 | 0.188 | vektoritietokantaan. Inferenssivaiheessa käyttäjän kielimallille lähet… |
| 5 | Rauten_Sami | Rauten Sami | 0.648 | 0.103 | vektorihakuteknologiaan. Käyttäjän esittämä kysymys muunnetaan numeeri… |

### Comparison (all configs)

| config_name | recall@k | nDCG@k | latency_ms |
| --- | --- | --- | --- |
| C0_baseline | 0.0000 | 0.0000 | 21.1 |
| C1_mmr | 0.0000 | 0.0000 | 18.6 |
| C2_mmr_rerank | 0.0000 | 0.0000 | 267.9 |
| C3_mmr_rerank_dedupe | 0.0000 | 0.0000 | 274.8 |

### Interpretation

- **Failure:** No gold items in top-k (recall@k=0).
- Gold did not appear in top-k or was ranked very low.

---

## Case 3 — q29

**Question:** Mitä on semanttinen haku ja miten se toimii?

**Gold (relevant_doc_ids):** Antikainen_Jari, Holopainen_Petri

**Focus config:** C2_mmr_rerank

**Metrics (focus config):** recall@k=0.0000, nDCG@k=0.0000, latency_ms=283.1

### Top hits (focus config, top K)

| rank | doc_id | title | score | rerank_score | snippet |
| --- | --- | --- | --- | --- | --- |
| 1 | Rauten_Sami | Rauten Sami | 0.559 | 0.552 | 2. Hybridihaku: vektorihaku ja fallback-mekanismi Esimerkkikoodi 2 hav… |
| 2 | Rauten_Sami | Rauten Sami | 0.590 | 0.233 | Search Vektorihaku. Hakumenetelmä, jossa kysely ja dokumentit muunneta… |
| 3 | Virtanen_Lauri | Virtanen Lauri | 0.520 | 0.116 | vektoreiksi. • Haku: relevanttien tekstikatkelmien haku semanttisesti.… |
| 4 | Rauten_Sami | Rauten Sami | 0.538 | 0.040 | varmistamisessa. 4 Järjestelmän suunnittelu ja toteutus Tämä järjestel… |
| 5 | Rauten_Sami | Rauten Sami | 0.588 | 0.030 | kulun. Kuvassa on esitetty, kuinka kysely etenee vektoripohjaisesta kä… |

### Comparison (all configs)

| config_name | recall@k | nDCG@k | latency_ms |
| --- | --- | --- | --- |
| C0_baseline | 0.5000 | 0.5000 | 23.4 |
| C1_mmr | 1.0000 | 0.5438 | 21.9 |
| C2_mmr_rerank | 0.0000 | 0.0000 | 283.1 |
| C3_mmr_rerank_dedupe | 0.0000 | 0.0000 | 269.8 |

### Interpretation

- **Failure:** No gold items in top-k (recall@k=0).
- Gold did not appear in top-k or was ranked very low.
- **Config disagreement:** Another config retrieved the gold; focus config (e.g. reranker) pushed it out of top-k.

---

## Case 4 — q1

**Question:** Mitä on RAG-järjestelmä ja miten se toimii?

**Gold (relevant_doc_ids):** Antikainen_Jari, Holopainen_Petri

**Focus config:** C2_mmr_rerank

**Metrics (focus config):** recall@k=1.0000, nDCG@k=0.5438, latency_ms=664.5

### Top hits (focus config, top K)

| rank | doc_id | title | score | rerank_score | snippet |
| --- | --- | --- | --- | --- | --- |
| 1 | Rauten_Sami | Rauten Sami | 0.575 | 0.957 | analyysin. RAG-arkkitehtuuri yhdistää semanttisen haun ja suurten kiel… |
| 2 | Pulli_Samu | Pulli Samu | 0.550 | 0.955 | Tähän ongelmaan tuli ehdotus ratkaisuksi Metalta vuonna 2020. Meta jul… |
| 3 | Holopainen_Petri | Holopainen Petri | 0.574 | 0.951 | monia. Esimerkiksi se voidaan yhdistää paikalliseen tietokantaan, tiet… |
| 4 | Myller_Niskanen_Rytilahti | Myller Niskanen Rytilahti | 0.565 | 0.942 | ketteryyteen. 5.8.3 Yksikkötestaus RAG-järjestelmässä RAG-järjestelmä … |
| 5 | Antikainen_Jari | Antikainen Jari | 0.587 | 0.936 | indeksointia. Laajemmin tarkasteltuna RAG-sovelluksen toiminta sisältä… |

### Comparison (all configs)

| config_name | recall@k | nDCG@k | latency_ms |
| --- | --- | --- | --- |
| C0_baseline | 0.5000 | 1.0000 | 1837.8 |
| C1_mmr | 0.5000 | 1.0000 | 45.5 |
| C2_mmr_rerank | 1.0000 | 0.5438 | 664.5 |
| C3_mmr_rerank_dedupe | 1.0000 | 0.5438 | 206.9 |

### Interpretation

- **Success:** All gold documents/chunks were retrieved in top-k.
- Gold appeared but ranking could be improved.
- **Config disagreement:** Different configs produced different recall; worth comparing.

---

## Case 5 — q2

**Question:** Miten vektoritietokanta toimii semanttisessa haussa?

**Gold (relevant_doc_ids):** Antikainen_Jari, Holopainen_Petri

**Focus config:** C2_mmr_rerank

**Metrics (focus config):** recall@k=0.5000, nDCG@k=0.3869, latency_ms=207.9

### Top hits (focus config, top K)

| rank | doc_id | title | score | rerank_score | snippet |
| --- | --- | --- | --- | --- | --- |
| 1 | Martin_Joel | Martin Joel | 0.817 | 0.995 | käyttötarkoituksiin. [27.] Toisin sanoen vektoritietokannat toimivat s… |
| 2 | Majander_Pyry | Majander Pyry | 0.761 | 0.990 | vektoritietokantaan. Inferenssivaiheessa käyttäjän kielimallille lähet… |
| 3 | Sarkiniemi_Mikko | Sarkiniemi Mikko | 0.725 | 0.987 | Kuva 3. Chunkkien luontiprosessi tietokantaan (mukaillen AI SDK s.a. a… |
| 4 | Martin_Joel | Martin Joel | 0.768 | 0.942 | generoinnissa. Aluksi tiedonlähteenä toimiva teksti pilkotaan sopiviin… |
| 5 | Antikainen_Jari | Antikainen Jari | 0.701 | 0.825 | (OllamaEmbeddings). Nämä upotukset kuvaavat palojen semanttista merkit… |

### Comparison (all configs)

| config_name | recall@k | nDCG@k | latency_ms |
| --- | --- | --- | --- |
| C0_baseline | 0.0000 | 0.0000 | 49.7 |
| C1_mmr | 0.0000 | 0.0000 | 27.9 |
| C2_mmr_rerank | 0.5000 | 0.3869 | 207.9 |
| C3_mmr_rerank_dedupe | 0.5000 | 0.3869 | 204.4 |

### Interpretation

- **Partial:** 50% of gold items retrieved (recall@k=0.50).
- Gold appeared but ranking could be improved.
- **Config disagreement:** Different configs produced different recall; worth comparing.

---

## Case 6 — q3

**Question:** Mitä hyötyä on hybridihakusta verrattuna pelkkään semanttiseen hakuun?

**Gold (relevant_doc_ids):** Antikainen_Jari

**Focus config:** C2_mmr_rerank

**Metrics (focus config):** recall@k=1.0000, nDCG@k=0.9675, latency_ms=256.4

### Top hits (focus config, top K)

| rank | doc_id | title | score | rerank_score | snippet |
| --- | --- | --- | --- | --- | --- |
| 1 | Antikainen_Jari | Antikainen Jari | 0.598 | 0.965 | Toteutettu RAG-järjestelmä osoittautui toimivaksi ja kykeni vastaamaan… |
| 2 | Antikainen_Jari | Antikainen Jari | 0.776 | 0.935 | datasta ne olennaisimmat tekstipalat (chunks), jotka sisältävät vastau… |
| 3 | Rauten_Sami | Rauten Sami | 0.641 | 0.359 | 2. Hybridihaku: vektorihaku ja fallback-mekanismi Esimerkkikoodi 2 hav… |
| 4 | Antikainen_Jari | Antikainen Jari | 0.667 | 0.334 | 5.3.2 Monikyselyhaku (Multi-Query Retrieval) Joskus käyttäjän alkuperä… |
| 5 | Sarkiniemi_Mikko | Sarkiniemi Mikko | 0.617 | 0.033 | vektoreihin. Toisin kuin perinteinen avainsanahaku, vektorihaku etsii … |

### Comparison (all configs)

| config_name | recall@k | nDCG@k | latency_ms |
| --- | --- | --- | --- |
| C0_baseline | 1.0000 | 1.0000 | 26.0 |
| C1_mmr | 1.0000 | 0.9197 | 25.8 |
| C2_mmr_rerank | 1.0000 | 0.9675 | 256.4 |
| C3_mmr_rerank_dedupe | 1.0000 | 0.9675 | 241.8 |

### Interpretation

- **Success:** All gold documents/chunks were retrieved in top-k.
- Gold was ranked highly (nDCG@k ≥ 0.9).

---

## Case 7 — q4

**Question:** Mitkä ovat paikallisen RAG-järjestelmän edut pilvipalveluihin verrattuna?

**Gold (relevant_doc_ids):** Antikainen_Jari

**Focus config:** C2_mmr_rerank

**Metrics (focus config):** recall@k=1.0000, nDCG@k=0.9675, latency_ms=223.0

### Top hits (focus config, top K)

| rank | doc_id | title | score | rerank_score | snippet |
| --- | --- | --- | --- | --- | --- |
| 1 | Antikainen_Jari | Antikainen Jari | 0.602 | 0.963 | 5 Toteutus: Paikallisen RAG-järjestelmän kehittäminen Tämän insinöörit… |
| 2 | Antikainen_Jari | Antikainen Jari | 0.727 | 0.948 | -menetelmää. Lisäksi työssä pyrittiin arvioimaan paikallisten LLM-pohj… |
| 3 | Sarkiniemi_Mikko | Sarkiniemi Mikko | 0.605 | 0.733 | Kehittäjien näkökulmasta RAG antaa paremman hallinnan ja ylläpidettävy… |
| 4 | Antikainen_Jari | Antikainen Jari | 0.607 | 0.495 | The implemented RAG system proved functional, capable of answering que… |
| 5 | Sarkiniemi_Mikko | Sarkiniemi Mikko | 0.536 | 0.064 | järjestelmä hyödyntää ulkoisia rajapintoja, API-avainten hallinta on e… |

### Comparison (all configs)

| config_name | recall@k | nDCG@k | latency_ms |
| --- | --- | --- | --- |
| C0_baseline | 1.0000 | 0.9829 | 26.2 |
| C1_mmr | 1.0000 | 1.0000 | 29.4 |
| C2_mmr_rerank | 1.0000 | 0.9675 | 223.0 |
| C3_mmr_rerank_dedupe | 1.0000 | 0.9675 | 227.9 |

### Interpretation

- **Success:** All gold documents/chunks were retrieved in top-k.
- Gold was ranked highly (nDCG@k ≥ 0.9).

---

## Case 8 — q7

**Question:** Mitä haasteita suurilla kielimalleilla on?

**Gold (relevant_doc_ids):** Antikainen_Jari, Holopainen_Petri

**Focus config:** C2_mmr_rerank

**Metrics (focus config):** recall@k=0.5000, nDCG@k=1.0000, latency_ms=1365.8

### Top hits (focus config, top K)

| rank | doc_id | title | score | rerank_score | snippet |
| --- | --- | --- | --- | --- | --- |
| 1 | Antikainen_Jari | Antikainen Jari | 0.643 | 0.996 | rajoituksia. Yksi merkittävimmistä haasteista on tuotetun sisällön tar… |
| 2 | Martin_Joel | Martin Joel | 0.672 | 0.962 | ongelmia. Vaikka kielimallit olivat nopeita tehtävissään, niiden ratka… |
| 3 | Majander_Pyry | Majander Pyry | 0.703 | 0.917 | Vaikka suuret kielimallit ovat osoittautuneet äärimmäisen hyödyllisiks… |
| 4 | Myller_Niskanen_Rytilahti | Myller Niskanen Rytilahti | 0.677 | 0.743 | 10 (48) 1 JOHDANTO Tekoäly on kehittynyt viime vuosina nopeaa tahtia, … |
| 5 | Martin_Joel | Martin Joel | 0.637 | 0.697 | suorituskyvystä. [34.] 3.2 Rajoitteet Lokaalien kielimallien rajoittei… |

### Comparison (all configs)

| config_name | recall@k | nDCG@k | latency_ms |
| --- | --- | --- | --- |
| C0_baseline | 0.0000 | 0.0000 | 26.0 |
| C1_mmr | 0.5000 | 0.6309 | 31.3 |
| C2_mmr_rerank | 0.5000 | 1.0000 | 1365.8 |
| C3_mmr_rerank_dedupe | 0.5000 | 1.0000 | 1372.9 |

### Interpretation

- **Partial:** 50% of gold items retrieved (recall@k=0.50).
- Gold was ranked highly (nDCG@k ≥ 0.9).
- **Latency outlier:** High latency may be due to cold start, reranker load, or hardware variance.

---
