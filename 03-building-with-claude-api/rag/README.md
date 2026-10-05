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

## Files

- `chunking.py` — the three chunkers, fixed, shared by every lesson from 02 on
- `report.md` — the sample document every lesson chunks and searches; "bug" means two
  different things in two of its sections, on purpose
- `01_introducing_rag.py` — what RAG is, and why not just send the whole document
- `02_text_chunking_strategies.py` — size, sentence and section chunking compared on one
  document: sizes, mid-word cuts, and chunks that straddle sections
- `03_text_embeddings.py` — text to vectors, so similar meaning becomes nearby vectors
- `04_full_rag_flow.py` — the pipeline end to end, before any code
- `05_implementing_rag_flow.py` — the pipeline as working code: index, search, prompt
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
