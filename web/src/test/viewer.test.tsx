import { render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import rawDataset from "../data/research-dataset.json";
import { App } from "../App";
import { filteredQuestionCsv, fullAggregateCsv } from "../download";
import { parseHash, serializeHash } from "../hashState";
import { filterQuestions, publishedAggregates } from "../selectors";
import type { Dataset } from "../types";

const dataset = rawDataset as Dataset;

describe("tallennettujen tulosten selain", () => {
  it("palauttaa virheellisen osoitteen yleiskuvaan ja säilyttää kelvollisen tilan", () => {
    const invalid = parseHash("#/puuttuu?run=ei&metric=f1&q=q99", dataset);
    expect(invalid.route).toBe("yleiskuva");
    expect(invalid.run).toBe("ablation");
    expect(invalid.metric).toBe("ndcg");
    expect(invalid.notices.length).toBeGreaterThan(0);
    const selected = parseHash("#/kysymykset?run=rerank&q=q6&metric=p95&search=cross", dataset);
    expect(serializeHash(selected, dataset)).toContain("#/kysymykset");
    expect(parseHash(serializeHash(selected, dataset), dataset).question).toBe("q6");
    expect(parseHash(serializeHash(selected, dataset), dataset).run).toBe("rerank");
  });

  it("jättää julkaistut keskiarvot ennalleen, kun kysymyslistaa suodatetaan", () => {
    const before = publishedAggregates(dataset, "ablation").map((row) => row.mean_recall_at_k);
    const filtered = filterQuestions(dataset.questions, "cross", "tekniikka");
    const after = publishedAggregates(dataset, "ablation").map((row) => row.mean_recall_at_k);
    expect(after).toEqual(before);
    expect(filtered.length).toBeLessThan(dataset.questions.length);
    const download = filteredQuestionCsv(dataset, "ablation", filtered);
    expect(download.csv).toContain("Suodatettu kysymyslista");
    expect(download.csv).not.toContain("mean_recall_at_k");
    const full = fullAggregateCsv(dataset, "ablation");
    expect(full.csv).toContain("Ei alkuperäinen opinnäytetyön tiedosto");
    expect(full.csv).toContain("0.65");
    expect(full.csv).toContain(dataset.original_experiment_commit);
  });

  it("näyttää tallennettujen tulosten rajan ja viisi näkymää", () => {
    window.location.hash = "#/yleiskuva";
    render(<App />);
    expect(screen.getByText("Opinnäytetyön tallennetut tutkimustulokset · Ei reaaliaikaista hakua")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Yleiskuva" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Hakustrategioiden vertailu" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Kysymyskohtaiset tulokset" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Laatu ja viive" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Menetelmät ja rajoitukset" })).toBeInTheDocument();
    expect(screen.queryByText(/Julkaisutarkistus on kesken/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Ei reaaliaikaista hakua/)).toBeInTheDocument();
  });

  it("vaihtaa näkymän hash-osoitteella", () => {
    function Probe() {
      const [hash, setHash] = useState("#/laatu?metric=p50");
      const state = parseHash(hash, dataset);
      return (
        <button type="button" onClick={() => setHash("#/menetelmat")}>
          {state.route}:{state.metric}
        </button>
      );
    }
    render(<Probe />);
    expect(screen.getByRole("button")).toHaveTextContent("laatu:p50");
  });
});
