# cpra-logprob-exp

An experiment in screening documents for responsiveness to California Public
Records Act (CPRA) requests using small, locally run language models — reading
the yes/no probability from the model's first output token instead of
generating an answer.

Motivation, hypotheses, metrics, dataset plan and phases are in [SPEC.md](SPEC.md).

Status: the experiment has run. Results are in
[docs/findings-golden.md](docs/findings-golden.md), with the supporting analysis in
[docs/analysis/](docs/analysis/). Earlier rounds are in `docs/findings-run1.md` and
`docs/findings-sweep.md`.

## Data

The repository holds the request texts, the document manifests, pair ids, labels,
model scores and the analysis. It does not hold the text of any email. The files
below exist only on the machine that ran the experiment and are git-ignored.

- **Real emails** (`data/emails/sandiego.emails.jsonl`). The corpus is public
  County of San Diego productions for requests 24-409, 25-3152, 25-4697 and 25-5982.
  `data/manifests/sandiego/` lists every document with its portal URL, so the corpus
  can be fetched again from the County's portal and parsed:

      uv run python scripts/acquire_sandiego.py download 24-409 25-3152 25-4697 25-5982
      uv run python scripts/parse_emails.py sandiego

- **Golden set** (`data/golden/emails.jsonl`, and the generation and pre-label work
  files under `data/golden/work/`). The ids, labels, pre-label rationales and
  adjudication calls are in the repository (`data/golden/pairs.jsonl`,
  `data/golden/work/prelabels.jsonl`, `data/golden/work/adjudications.json`). The
  email text is not, and that includes the 226 synthetic emails, which cannot be
  regenerated exactly.
- **Review sheets** (`docs/golden-adjudication.md`, `docs/golden-adjudication.html`,
  `docs/spotcheck-qwen3.5-4b.md`). These quote emails at length. The findings refer
  to them as "local only".

The scoring scripts, several of the analysis scripts and `explainer/build_data.py` read
the email files, so they need a local copy. The tracked `runs/*/scores.jsonl` files
carry scores without email text, apart from short phrases a model quoted in its
written reasoning.

## Layer looping (side experiment)

`loop/` is a separate PyTorch harness that runs some of a stock model's layers twice and scores the
golden set the same way. Result: a small gain on Qwen3.5-4B that did not replicate on Qwen3.5-9B, for 5 to
12% more time. See [docs/findings-looping.md](docs/findings-looping.md).

## Explainer

`explainer/` is the source of a private explainer page and of two cuts of a short
video. `explainer/data.js` carries email excerpts and is git-ignored, so the page
needs the local data. The videos use invented emails and anonymous scores only.
Rendered video, generated audio and the downloaded font files are not committed.
