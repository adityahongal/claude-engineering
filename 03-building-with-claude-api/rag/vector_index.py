"""A minimal vector store — the VectorIndex the course hands out, written out.

Shared by 05 onwards. It is a list and a loop: every search compares the query against
every stored vector. A real vector database (pgvector, Atlas Vector Search, ...) does the
same comparison but with an index that avoids touching every vector — the results are the
same, only the speed differs, and at a dozen chunks speed is not the problem.

Each entry keeps the vector AND the document it came from. The vector is only how you
find a chunk; the text is what goes in the prompt, so storing one without the other is
useless.

Two ways in, because two lessons use it differently:

    05   add_vector(vector, doc) / search(vector)   — you embed, the index stores
    07   add_documents(docs) / search("text")       — the index embeds, so it can sit
                                                      behind the same interface as BM25Index

add_documents() embeds the whole list in ONE request. The course's add_document() embeds
per call, and at 3 requests a minute (Voyage, no payment method) a dozen chunks would
take four minutes.
"""

from embeddings import cosine, embed


class VectorIndex:
    def __init__(self):
        self.vectors = []
        self.documents = []

    # ── 05: bring your own vectors ───────────────────────────────────────────────────

    def add_vector(self, vector: list, document: dict) -> None:
        if self.vectors and len(vector) != len(self.vectors[0]):
            # Mixing models (or dimension settings) makes every comparison meaningless, and
            # nothing else would catch it.
            raise ValueError(f"vector has {len(vector)} dimensions; "
                             f"the index holds {len(self.vectors[0])}")
        self.vectors.append(vector)
        self.documents.append(document)

    # ── 07: the shared SearchIndex interface ─────────────────────────────────────────

    def add_documents(self, documents: list) -> None:
        """Embed every document's "content" in one request, then store each."""
        vectors = embed([doc["content"] for doc in documents], input_type="document")
        for vector, document in zip(vectors.embeddings, documents):
            self.add_vector(vector, document)

    def add_document(self, document: dict) -> None:
        self.add_documents([document])

    def search(self, query, k: int = 1) -> list:
        """The k nearest documents as (document, cosine distance), nearest first.

        `query` is a vector, or text — text is embedded as a "query" first (one request).
        Distance, not similarity, to match the course: 1 - cosine, so lower is better.
        """
        if isinstance(query, str):
            query = embed([query], input_type="query").embeddings[0]
        scored = [(doc, 1 - cosine(query, vec))
                  for vec, doc in zip(self.vectors, self.documents)]
        scored.sort(key=lambda pair: pair[1])
        return scored[:k]

    def __len__(self) -> int:
        return len(self.vectors)
