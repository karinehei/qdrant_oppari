# Liite X. Kysymys–haku–vastaus -esimerkit (RAG-putki)

Tässä liitteessä esitetään valitut esimerkkitapaukset RAG-putken hakutuloksista. Jokaisessa tapauksessa näytetään kysymys, haetut lähteet (top-k), mittarit (recall@k, nDCG@k, latenssi) ja lyhyt tulkinta. Taulukot esittävät sijoituksen, lähteen (doc_id), otsikon, pisteen ja mahdollisesti rerank-pisteen sekä lyhyen katkelman.

## Liitteen lukeminen ja gold-annotointi

- **Gold** tarkoittaa tässä liitteessä kysymyksen kannalta relevantteja dokumentteja (doc-tason arviointi). Gold-lähteet on annotoitu etukäteen; ne toimivat vertailupohjana hakutulosten arvioinnissa.
- **Relevanssi** on binäärinen (relevantti / ei relevantti), ellei toisin mainita.
- **eval_level=doc** tarkoittaa, että arviointi tehdään dokumenttitasolla: sama dokumentti voi tuottaa useita top-k-rivejä, koska hausta palautuu eri katkelmat (chunks) samasta dokumentista.
- **Toistuva doc_id** top-k-taulukossa ei siis tarkoita useita erillisiä dokumentteja vaan eri katkelmia samasta lähteestä.
- **recall@k** kuvaa sitä, kuinka suuri osa gold-dokumenteista löytyi top-k-tuloksista (0–1).
- **nDCG@k** mittaa hakutulosten järjestystä: mitä korkeammalle gold sijoittuu, sitä parempi nDCG.
- **latenssi_ms** on mitattu kokeen toteutuksen mukaisesti ja kattaa vähintään haun; tarkka mittauskohta on dokumentoitu run_metadata.json-tiedostoon.
- **Katkelmat** on rajattu lyhyiksi (truncated) tekijänoikeussyistä; ne eivät korvaa alkuperäistä lähdettä.

## Ajo- ja kokoelmatiedot

- **Ajoajankohta:** 2026-02-27 10:30 UTC
- **Kokoelma:** rag_thesis_fi
- **top_k:** 5
- **initial_limit:** 20
- **score_threshold:** 0.0
- **eval_level:** doc
- **seed:** 42
- **Rerank-malli(t):** ['BAAI/bge-reranker-v2-m3']

---

## X.1 q6

**Kysymys:** Miten cross-encoder parantaa hakutulosten relevanssia?

**Gold (relevantit lähteet):** Antikainen_Jari

**Konfiguraatio:** C2_mmr_rerank

**Mittarit (recall@k, nDCG@k, latenssi):** recall@k=1.0000, nDCG@k=1.0000, latenssi_ms=1141.8

### Hakutulokset (top-k)

Huom: doc-tason arvioinnissa sama doc_id voi esiintyä useana rivinä (eri katkelmat samasta dokumentista).

| Sijoitus | Lähde (doc_id/source) | Otsikko | Piste (score) | Rerank-piste | Katkelma |
| --- | --- | --- | --- | --- | --- |
| 1 | Antikainen_Jari | Antikainen Jari | 0.685 | 0.919 | 2. Uudelleenjärjestäminen (Re-ranking): Cross-encoder-pohjainen uudell… |
| 2 | Antikainen_Jari | Antikainen Jari | 0.648 | 0.900 | (esim. hybridi- tai monikyselyhakija) hakee laajemman joukon dokumentt… |
| 3 | Sarkiniemi_Mikko | Sarkiniemi Mikko | 0.686 | 0.041 | sisältöihin. Tämä parantaa hakutulosten relevanssia ja RAG-mallin tuot… |
| 4 | Martin_Joel | Martin Joel | 0.698 | 0.015 | muotoon. Myös kysymysten esikäsittely voi parantaa tuloksia muotoilema… |
| 5 | Sarkiniemi_Mikko | Sarkiniemi Mikko | 0.632 | 0.013 | mahdollistaa tarkemmat ja relevantimmat hakutulokset. Nämä auttavat LL… |

### Vertailu (kaikki konfiguraatiot)

| Konfiguraatio | recall@k | nDCG@k | latenssi_ms |
| --- | --- | --- | --- |
| C0_baseline | 1.0000 | 0.5438 | 35.8 |
| C1_mmr | 1.0000 | 0.5438 | 34.5 |
| C2_mmr_rerank | 1.0000 | 1.0000 | 1141.8 |
| C3_mmr_rerank_dedupe | 1.0000 | 1.0000 | 1140.6 |

### Tulkinta

- **Onnistui:** Kaikki gold-dokumentit löytyivät top-k:sta.
- Gold sijoittui korkealle (nDCG@k ≥ 0,9).

---

## X.2 q24

**Kysymys:** Miten vektoritietokanta eroaa perinteisestä tietokannasta?

**Gold (relevantit lähteet):** Antikainen_Jari, Holopainen_Petri

**Konfiguraatio:** C2_mmr_rerank

**Mittarit (recall@k, nDCG@k, latenssi):** recall@k=0.0000, nDCG@k=0.0000, latenssi_ms=267.9

### Hakutulokset (top-k)

Huom: doc-tason arvioinnissa sama doc_id voi esiintyä useana rivinä (eri katkelmat samasta dokumentista).

| Sijoitus | Lähde (doc_id/source) | Otsikko | Piste (score) | Rerank-piste | Katkelma |
| --- | --- | --- | --- | --- | --- |
| 1 | Pulli_Samu | Pulli Samu | 0.782 | 0.993 | 3.2.2 Vektoritietokannat Vektoritietokanta on kokoelma numeroilla esit… |
| 2 | Majander_Pyry | Majander Pyry | 0.649 | 0.548 | Kuva 9. Sanojen vektoriesitykset euklidisessa avaruudessa (mukaillen K… |
| 3 | Martin_Joel | Martin Joel | 0.719 | 0.442 | käyttötarkoituksiin. [27.] Toisin sanoen vektoritietokannat toimivat s… |
| 4 | Majander_Pyry | Majander Pyry | 0.716 | 0.188 | vektoritietokantaan. Inferenssivaiheessa käyttäjän kielimallille lähet… |
| 5 | Rauten_Sami | Rauten Sami | 0.648 | 0.103 | vektorihakuteknologiaan. Käyttäjän esittämä kysymys muunnetaan numeeri… |

### Vertailu (kaikki konfiguraatiot)

| Konfiguraatio | recall@k | nDCG@k | latenssi_ms |
| --- | --- | --- | --- |
| C0_baseline | 0.0000 | 0.0000 | 21.1 |
| C1_mmr | 0.0000 | 0.0000 | 18.6 |
| C2_mmr_rerank | 0.0000 | 0.0000 | 267.9 |
| C3_mmr_rerank_dedupe | 0.0000 | 0.0000 | 274.8 |

### Tulkinta

- **Epäonnistui:** Yhtään gold-kohdetta ei löytynyt top-k:sta (recall@k=0).
- Gold ei löytynyt top-k:sta tai sijoittui hyvin alas.
- Tässä yksittäisessä tapauksessa deduplikointi ei pienentänyt latenssia, mikä viittaa siihen, että latenssiin vaikuttavat myös ajonaikaiset tekijät (kuorma, outlierit) eikä pelkästään rerankattavien kandidaattien määrä.

---

## X.3 q29

**Kysymys:** Mitä on semanttinen haku ja miten se toimii?

**Gold (relevantit lähteet):** Antikainen_Jari, Holopainen_Petri

**Konfiguraatio:** C2_mmr_rerank

**Mittarit (recall@k, nDCG@k, latenssi):** recall@k=0.0000, nDCG@k=0.0000, latenssi_ms=283.1

### Hakutulokset (top-k)

Huom: doc-tason arvioinnissa sama doc_id voi esiintyä useana rivinä (eri katkelmat samasta dokumentista).

| Sijoitus | Lähde (doc_id/source) | Otsikko | Piste (score) | Rerank-piste | Katkelma |
| --- | --- | --- | --- | --- | --- |
| 1 | Rauten_Sami | Rauten Sami | 0.559 | 0.552 | 2. Hybridihaku: vektorihaku ja fallback-mekanismi Esimerkkikoodi 2 hav… |
| 2 | Rauten_Sami | Rauten Sami | 0.590 | 0.233 | Search Vektorihaku. Hakumenetelmä, jossa kysely ja dokumentit muunneta… |
| 3 | Virtanen_Lauri | Virtanen Lauri | 0.520 | 0.116 | vektoreiksi. • Haku: relevanttien tekstikatkelmien haku semanttisesti.… |
| 4 | Rauten_Sami | Rauten Sami | 0.538 | 0.040 | varmistamisessa. 4 Järjestelmän suunnittelu ja toteutus Tämä järjestel… |
| 5 | Rauten_Sami | Rauten Sami | 0.588 | 0.030 | kulun. Kuvassa on esitetty, kuinka kysely etenee vektoripohjaisesta kä… |

### Vertailu (kaikki konfiguraatiot)

| Konfiguraatio | recall@k | nDCG@k | latenssi_ms |
| --- | --- | --- | --- |
| C0_baseline | 0.5000 | 0.5000 | 23.4 |
| C1_mmr | 1.0000 | 0.5438 | 21.9 |
| C2_mmr_rerank | 0.0000 | 0.0000 | 283.1 |
| C3_mmr_rerank_dedupe | 0.0000 | 0.0000 | 269.8 |

### Tulkinta

- **Epäonnistui:** Yhtään gold-kohdetta ei löytynyt top-k:sta (recall@k=0).
- Gold ei löytynyt top-k:sta tai sijoittui hyvin alas.
- **Konfiguraatioero:** Toinen konfiguraatio haki goldin; fokus-konfiguraatio (esim. reranker) työnsi sen top-k:n ulkopuolelle.

---

## X.4 q1

**Kysymys:** Mitä on RAG-järjestelmä ja miten se toimii?

**Gold (relevantit lähteet):** Antikainen_Jari, Holopainen_Petri

**Konfiguraatio:** C2_mmr_rerank

**Mittarit (recall@k, nDCG@k, latenssi):** recall@k=1.0000, nDCG@k=0.5438, latenssi_ms=664.5

### Hakutulokset (top-k)

Huom: doc-tason arvioinnissa sama doc_id voi esiintyä useana rivinä (eri katkelmat samasta dokumentista).

| Sijoitus | Lähde (doc_id/source) | Otsikko | Piste (score) | Rerank-piste | Katkelma |
| --- | --- | --- | --- | --- | --- |
| 1 | Rauten_Sami | Rauten Sami | 0.575 | 0.957 | analyysin. RAG-arkkitehtuuri yhdistää semanttisen haun ja suurten kiel… |
| 2 | Pulli_Samu | Pulli Samu | 0.550 | 0.955 | Tähän ongelmaan tuli ehdotus ratkaisuksi Metalta vuonna 2020. Meta jul… |
| 3 | Holopainen_Petri | Holopainen Petri | 0.574 | 0.951 | monia. Esimerkiksi se voidaan yhdistää paikalliseen tietokantaan, tiet… |
| 4 | Myller_Niskanen_Rytilahti | Myller Niskanen Rytilahti | 0.565 | 0.942 | ketteryyteen. 5.8.3 Yksikkötestaus RAG-järjestelmässä RAG-järjestelmä … |
| 5 | Antikainen_Jari | Antikainen Jari | 0.587 | 0.936 | indeksointia. Laajemmin tarkasteltuna RAG-sovelluksen toiminta sisältä… |

### Vertailu (kaikki konfiguraatiot)

| Konfiguraatio | recall@k | nDCG@k | latenssi_ms |
| --- | --- | --- | --- |
| C0_baseline | 0.5000 | 1.0000 | 1837.8 |
| C1_mmr | 0.5000 | 1.0000 | 45.5 |
| C2_mmr_rerank | 1.0000 | 0.5438 | 664.5 |
| C3_mmr_rerank_dedupe | 1.0000 | 0.5438 | 206.9 |

### Tulkinta

- **Onnistui:** Kaikki gold-dokumentit löytyivät top-k:sta.
- Gold löytyi, mutta järjestystä voisi parantaa.
- **Konfiguraatioero:** Eri konfiguraatiot tuottivat eri recall-arvot; vertailun arvoista.

---

## X.5 q2

**Kysymys:** Miten vektoritietokanta toimii semanttisessa haussa?

**Gold (relevantit lähteet):** Antikainen_Jari, Holopainen_Petri

**Konfiguraatio:** C2_mmr_rerank

**Mittarit (recall@k, nDCG@k, latenssi):** recall@k=0.5000, nDCG@k=0.3869, latenssi_ms=207.9

### Hakutulokset (top-k)

Huom: doc-tason arvioinnissa sama doc_id voi esiintyä useana rivinä (eri katkelmat samasta dokumentista).

| Sijoitus | Lähde (doc_id/source) | Otsikko | Piste (score) | Rerank-piste | Katkelma |
| --- | --- | --- | --- | --- | --- |
| 1 | Martin_Joel | Martin Joel | 0.817 | 0.995 | käyttötarkoituksiin. [27.] Toisin sanoen vektoritietokannat toimivat s… |
| 2 | Majander_Pyry | Majander Pyry | 0.761 | 0.990 | vektoritietokantaan. Inferenssivaiheessa käyttäjän kielimallille lähet… |
| 3 | Sarkiniemi_Mikko | Sarkiniemi Mikko | 0.725 | 0.987 | Kuva 3. Chunkkien luontiprosessi tietokantaan (mukaillen AI SDK s.a. a… |
| 4 | Martin_Joel | Martin Joel | 0.768 | 0.942 | generoinnissa. Aluksi tiedonlähteenä toimiva teksti pilkotaan sopiviin… |
| 5 | Antikainen_Jari | Antikainen Jari | 0.701 | 0.825 | (OllamaEmbeddings). Nämä upotukset kuvaavat palojen semanttista merkit… |

### Vertailu (kaikki konfiguraatiot)

| Konfiguraatio | recall@k | nDCG@k | latenssi_ms |
| --- | --- | --- | --- |
| C0_baseline | 0.0000 | 0.0000 | 49.7 |
| C1_mmr | 0.0000 | 0.0000 | 27.9 |
| C2_mmr_rerank | 0.5000 | 0.3869 | 207.9 |
| C3_mmr_rerank_dedupe | 0.5000 | 0.3869 | 204.4 |

### Tulkinta

- **Osittain:** 50% gold-kohteista löytyi top-k:sta (recall@k=0,50).
- Gold löytyi, mutta järjestystä voisi parantaa.
- **Konfiguraatioero:** Eri konfiguraatiot tuottivat eri recall-arvot; vertailun arvoista.

---

## X.6 q3

**Kysymys:** Mitä hyötyä on hybridihakusta verrattuna pelkkään semanttiseen hakuun?

**Gold (relevantit lähteet):** Antikainen_Jari

**Konfiguraatio:** C2_mmr_rerank

**Mittarit (recall@k, nDCG@k, latenssi):** recall@k=1.0000, nDCG@k=0.9675, latenssi_ms=256.4

### Hakutulokset (top-k)

Huom: doc-tason arvioinnissa sama doc_id voi esiintyä useana rivinä (eri katkelmat samasta dokumentista).

| Sijoitus | Lähde (doc_id/source) | Otsikko | Piste (score) | Rerank-piste | Katkelma |
| --- | --- | --- | --- | --- | --- |
| 1 | Antikainen_Jari | Antikainen Jari | 0.598 | 0.965 | Toteutettu RAG-järjestelmä osoittautui toimivaksi ja kykeni vastaamaan… |
| 2 | Antikainen_Jari | Antikainen Jari | 0.776 | 0.935 | datasta ne olennaisimmat tekstipalat (chunks), jotka sisältävät vastau… |
| 3 | Rauten_Sami | Rauten Sami | 0.641 | 0.359 | 2. Hybridihaku: vektorihaku ja fallback-mekanismi Esimerkkikoodi 2 hav… |
| 4 | Antikainen_Jari | Antikainen Jari | 0.667 | 0.334 | 5.3.2 Monikyselyhaku (Multi-Query Retrieval) Joskus käyttäjän alkuperä… |
| 5 | Sarkiniemi_Mikko | Sarkiniemi Mikko | 0.617 | 0.033 | vektoreihin. Toisin kuin perinteinen avainsanahaku, vektorihaku etsii … |

### Vertailu (kaikki konfiguraatiot)

| Konfiguraatio | recall@k | nDCG@k | latenssi_ms |
| --- | --- | --- | --- |
| C0_baseline | 1.0000 | 1.0000 | 26.0 |
| C1_mmr | 1.0000 | 0.9197 | 25.8 |
| C2_mmr_rerank | 1.0000 | 0.9675 | 256.4 |
| C3_mmr_rerank_dedupe | 1.0000 | 0.9675 | 241.8 |

### Tulkinta

- **Onnistui:** Kaikki gold-dokumentit löytyivät top-k:sta.
- Gold sijoittui korkealle (nDCG@k ≥ 0,9).

---

## X.7 q4

**Kysymys:** Mitkä ovat paikallisen RAG-järjestelmän edut pilvipalveluihin verrattuna?

**Gold (relevantit lähteet):** Antikainen_Jari

**Konfiguraatio:** C2_mmr_rerank

**Mittarit (recall@k, nDCG@k, latenssi):** recall@k=1.0000, nDCG@k=0.9675, latenssi_ms=223.0

### Hakutulokset (top-k)

Huom: doc-tason arvioinnissa sama doc_id voi esiintyä useana rivinä (eri katkelmat samasta dokumentista).

| Sijoitus | Lähde (doc_id/source) | Otsikko | Piste (score) | Rerank-piste | Katkelma |
| --- | --- | --- | --- | --- | --- |
| 1 | Antikainen_Jari | Antikainen Jari | 0.602 | 0.963 | 5 Toteutus: Paikallisen RAG-järjestelmän kehittäminen Tämän insinöörit… |
| 2 | Antikainen_Jari | Antikainen Jari | 0.727 | 0.948 | -menetelmää. Lisäksi työssä pyrittiin arvioimaan paikallisten LLM-pohj… |
| 3 | Sarkiniemi_Mikko | Sarkiniemi Mikko | 0.605 | 0.733 | Kehittäjien näkökulmasta RAG antaa paremman hallinnan ja ylläpidettävy… |
| 4 | Antikainen_Jari | Antikainen Jari | 0.607 | 0.495 | The implemented RAG system proved functional, capable of answering que… |
| 5 | Sarkiniemi_Mikko | Sarkiniemi Mikko | 0.536 | 0.064 | järjestelmä hyödyntää ulkoisia rajapintoja, API-avainten hallinta on e… |

### Vertailu (kaikki konfiguraatiot)

| Konfiguraatio | recall@k | nDCG@k | latenssi_ms |
| --- | --- | --- | --- |
| C0_baseline | 1.0000 | 0.9829 | 26.2 |
| C1_mmr | 1.0000 | 1.0000 | 29.4 |
| C2_mmr_rerank | 1.0000 | 0.9675 | 223.0 |
| C3_mmr_rerank_dedupe | 1.0000 | 0.9675 | 227.9 |

### Tulkinta

- **Onnistui:** Kaikki gold-dokumentit löytyivät top-k:sta.
- Gold sijoittui korkealle (nDCG@k ≥ 0,9).
- Tässä yksittäisessä tapauksessa deduplikointi ei pienentänyt latenssia, mikä viittaa siihen, että latenssiin vaikuttavat myös ajonaikaiset tekijät (kuorma, outlierit) eikä pelkästään rerankattavien kandidaattien määrä.

---

## X.8 q7

**Kysymys:** Mitä haasteita suurilla kielimalleilla on?

**Gold (relevantit lähteet):** Antikainen_Jari, Holopainen_Petri

**Konfiguraatio:** C2_mmr_rerank

**Mittarit (recall@k, nDCG@k, latenssi):** recall@k=0.5000, nDCG@k=1.0000, latenssi_ms=1365.8

### Hakutulokset (top-k)

Huom: doc-tason arvioinnissa sama doc_id voi esiintyä useana rivinä (eri katkelmat samasta dokumentista).

| Sijoitus | Lähde (doc_id/source) | Otsikko | Piste (score) | Rerank-piste | Katkelma |
| --- | --- | --- | --- | --- | --- |
| 1 | Antikainen_Jari | Antikainen Jari | 0.643 | 0.996 | rajoituksia. Yksi merkittävimmistä haasteista on tuotetun sisällön tar… |
| 2 | Martin_Joel | Martin Joel | 0.672 | 0.962 | ongelmia. Vaikka kielimallit olivat nopeita tehtävissään, niiden ratka… |
| 3 | Majander_Pyry | Majander Pyry | 0.703 | 0.917 | Vaikka suuret kielimallit ovat osoittautuneet äärimmäisen hyödyllisiks… |
| 4 | Myller_Niskanen_Rytilahti | Myller Niskanen Rytilahti | 0.677 | 0.743 | 10 (48) 1 JOHDANTO Tekoäly on kehittynyt viime vuosina nopeaa tahtia, … |
| 5 | Martin_Joel | Martin Joel | 0.637 | 0.697 | suorituskyvystä. [34.] 3.2 Rajoitteet Lokaalien kielimallien rajoittei… |

### Vertailu (kaikki konfiguraatiot)

| Konfiguraatio | recall@k | nDCG@k | latenssi_ms |
| --- | --- | --- | --- |
| C0_baseline | 0.0000 | 0.0000 | 26.0 |
| C1_mmr | 0.5000 | 0.6309 | 31.3 |
| C2_mmr_rerank | 0.5000 | 1.0000 | 1365.8 |
| C3_mmr_rerank_dedupe | 0.5000 | 1.0000 | 1372.9 |

### Tulkinta

- **Osittain:** 50% gold-kohteista löytyi top-k:sta (recall@k=0,50).
- Gold sijoittui korkealle (nDCG@k ≥ 0,9).
- **Latenssi-poikkeama:** Latenssi voi liittyä esimerkiksi yksittäiseen hitaaseen hakuun tai ajonaikaiseen kuormitukseen; poikkeamat varmistetaan per-kysely-tasolla (per_query_metrics.csv).
- Tässä yksittäisessä tapauksessa deduplikointi ei pienentänyt latenssia, mikä viittaa siihen, että latenssiin vaikuttavat myös ajonaikaiset tekijät (kuorma, outlierit) eikä pelkästään rerankattavien kandidaattien määrä.

---

## Yhteenveto liitteen havainnoista

- Näissä esimerkeissä baseline (C0) ja MMR (C1) hakivat goldin usein, kun taas rerank-konfiguraatiot (C2, C3) eivät aina löytäneet sitä.
- Rerank paransi järjestystä (nDCG) kun gold oli top-k:ssa, mutta joissakin tapauksissa rerank työnsi goldin ulos top-k:sta.
- Konfiguraatioeroja esiintyi: C1 haki goldin joissakin tapauksissa, joissa C2 epäonnistui.
- Latenssi vaihteli voimakkaasti konfiguraatioittain; rerank-konfiguraatiot olivat tyypillisesti hitaimpia.
- Deduplikointi (C3) pienensi latenssia useissa tapauksissa verrattuna C2:een, mutta ei aina.
- Osittaiset tulokset (recall@k < 1) esiintyivät tapauksissa, joissa gold-dokumentteja oli useita.
- Katkelmat on rajattu lyhyiksi; alkuperäiset lähteet tulee tarkistaa erikseen.
