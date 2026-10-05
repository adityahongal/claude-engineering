# RAG and Agentic Search

Retrieval Augmented Generation: answering from your own documents without pasting all of
them into the prompt. Split the documents into chunks, find the few chunks that bear on
the question, and send only those alongside it. Every lesson in this folder is one stage
of that pipeline, or a better way to do the "find" step.

## Files

- `01_introducing_rag.py` — what RAG is, and why not just send the whole document
- `02_text_chunking_strategies.py` — splitting documents by size, sentence, or structure
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
