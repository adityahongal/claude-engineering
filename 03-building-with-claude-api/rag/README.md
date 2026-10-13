# RAG and Agentic Search

Retrieval Augmented Generation: answering from your own documents without pasting all of
them into the prompt. Split the documents into chunks, find the few chunks that bear on
the question, and send only those alongside it. Every lesson in this folder is one stage
of that pipeline, or a better way to do the "find" step.

## Gotchas

- **Two of the course's chunkers have bugs.** `chunk_by_sentence` emits a duplicate tail
  (5 sentences, 5 per chunk, overlap 1 → `['A. B. C. D. E.', 'E.']`), and both it and
  `chunk_by_char` loop forever if the overlap is >= the chunk size. `chunk_by_section`'s
  `re.split(r"\n## ")` strips the `## ` from every header after the first. All fixed in
  `chunking.py`.
- **Overlap does not prevent mid-word cuts — measured.** Character chunks of 150 with 20
  overlap on `report.md`: 14 of 24 chunk edges land inside a word. The overlap copies the
  last 20 characters wherever they happen to start; what it buys is that a short sentence
  cut at a boundary is whole in one of the two chunks.
- **Sentence chunking ignores structure as much as size chunking does — measured.** On a
  Markdown document, 5 of 6 sentence chunks and 5 of 13 character chunks straddle a section
  header; section chunks, 0 of 6. A header line has no full stop, so the sentence splitter
  glues it onto the next sentence, mid-chunk.
- **The naive sentence regex splits on abbreviations.** `Dr. Okafor` and `e.g. on` both end
  a "sentence" — and each fake sentence counts against the per-chunk limit.

- **The course's `generate_embedding()` defaults `input_type` to `"query"`.** Chunks are
  documents, not questions. The same text as query vs document scored cosine 0.958 — a
  different vector. `embeddings.py` makes every call name its input type.
- **Embed in batches — on a free Voyage account it is not optional.** With no payment method
  the limit is 3 requests and 10K tokens a minute, and the SDK does not retry by default.
  The course's one-call-per-chunk loop failed on the fourth chunk; one batched call embeds
  all six. `embeddings.py` also turns on retries with backoff.
- **"Each number ranges from -1 to +1" undersells it.** Voyage vectors have length exactly
  1.0 over 1,024 numbers, so each is about ±0.1 — and the dot product of two of them is
  their cosine similarity.
- **Embeddings are only nearly deterministic — measured.** Batched vs alone differs by up to
  ~7e-4 per number, and batched results shifted between runs; cosine between variants
  0.99997. Never compare vectors with `==`.
- **One of the course's similarity numbers is wrong.** In the two-number example, the query vs
  the medical chunk is given as 0.398; the cosine is 0.434. 0.398 is the raw dot product
  taken before normalising — the 0.983 beside it is computed correctly, so the slide mixes
  the two. On unit vectors the dot product is the cosine; on raw ones a longer vector wins
  for being long.
- **Watch the margin, not just the winner.** The course's result wins by 0.01 (0.71 vs 0.72)
  — a coin toss. On `report.md` all four test questions found the right section with margins
  of 0.137 to 0.212.
- **`k` decides what else rides along.** "How many bugs did engineers fix?" ranks Software
  Engineering first (0.365) and Medical Research — the stomach bug — second (0.577). With
  `k=2`, the wrong-context chunk from 02 lands in the prompt anyway; the prompt tells Claude
  to use only what answers the question.
- **A MongoDB Atlas key (`al-...`) needs no endpoint setting.** The `voyageai` SDK routes it to
  `ai.mongodb.com` by its prefix.

## Files

- `chunking.py` — the three chunkers, fixed, shared by every lesson from 02 on
- `embeddings.py` — the Voyage client, batched `embed()`, `generate_embedding()`, `cosine()`
- `vector_index.py` — the course's `VectorIndex`, written out: vectors stored with their
  text, searched by cosine distance
- `report.md` — the sample document every lesson chunks and searches; "bug" means two
  different things in two of its sections, on purpose
- `01_introducing_rag.py` — what RAG is, and why not just send the whole document
- `02_text_chunking_strategies.py` — size, sentence and section chunking compared on one
  document: sizes, mid-word cuts, and chunks that straddle sections
- `03_text_embeddings.py` — what a vector looks like, batching under a 3-a-minute limit, and
  query vs document input types
- `04_full_rag_flow.py` — the course's two-number example recomputed, with no API call
- `05_implementing_rag_flow.py` — the pipeline as working code: index, search, margins, and
  the prompt it would send
- `06_bm25_lexical_search.py` — ranking by the words a chunk actually contains
- `07_multi_index_rag_pipeline.py` — semantic and lexical search together, rankings merged

Lesson files are numbered so the folder reads in course order. As in `tool-use/`, a
numbered file can be run but never imported, so anything two lessons share goes in a
plainly named module.

## Run

```bash
cd 03-building-with-claude-api/rag
python 02_text_chunking_strategies.py
```

The virtual environment and `.env` are shared — see the [module README](../README.md#setup).
