"""A minimal vector store — the VectorIndex the course hands out, written out.

Shared by 05 onwards. It is a list and a loop: every search compares the query against
every stored vector. A real vector database (pgvector, Atlas Vector Search, ...) does the
same comparison but with an index that avoids touching every vector — the results are the
same, only the speed differs, and at six chunks speed is not the problem.

Each entry keeps the vector AND the document it came from. The vector is only how you
find a chunk; the text is what goes in the prompt, so storing one without the other is
useless.
"""

from embeddings import cosine


class VectorIndex:
    def __init__(self):
        self.vectors = []
        self.documents = []

    def add_vector(self, vector: list, document: dict) -> None:
        if self.vectors and len(vector) != len(self.vectors[0]):
            # Mixing models (or dimension settings) makes every comparison meaningless, and
            # nothing else would catch it.
            raise ValueError(f"vector has {len(vector)} dimensions; "
                             f"the index holds {len(self.vectors[0])}")
        self.vectors.append(vector)
        self.documents.append(document)

    def search(self, query_vector: list, k: int = 1) -> list:
        """The k nearest documents as (document, cosine distance), nearest first.

        Distance, not similarity, to match the course: 1 - cosine, so 0 is identical and
        larger is further away — "lower is better".
        """
        scored = [(doc, 1 - cosine(query_vector, vec))
                  for vec, doc in zip(self.vectors, self.documents)]
        scored.sort(key=lambda pair: pair[1])
        return scored[:k]

    def __len__(self) -> int:
        return len(self.vectors)
