"""BM25 lexical search — the BM25Index the course hands out, written out.

Shared by 06 onwards. Same interface as VectorIndex — add_document(s) and search(text, k)
— so 07's Retriever can hold one of each without knowing which is which.

The scoring is standard Okapi BM25:

    score(doc) = Σ over query terms t of
                 idf(t) · tf · (k1 + 1) / (tf + k1 · (1 − b + b · len(doc) / avg_len))

    tf      how often t appears in this document
    idf(t)  how RARE t is across all documents — ln(1 + (N − n + 0.5) / (n + 0.5)),
            where n of the N documents contain it. A term in every document scores ~0.
    k1      how fast repeating a term stops helping (saturation). 1.5 is customary.
    b       how much a long document is penalised for being long. 0.75 is customary.

Two things the course's description smooths over:

  * Common words are not IGNORED, they are down-weighted — by how common they are IN THIS
    COLLECTION. "the" in every chunk has an idf near zero. But in 11 chunks, "what" and
    "happened" each appear in one, so they weigh exactly as much as "011": measured in 06,
    "What happened with INC-2026-Q3-011?" ranked the incident log's intro ("each entry
    records what happened") above the incident itself. Pass stopwords=STOPWORDS to drop
    question words before scoring.
  * The tokenizer decides what a "term" is. This one lowercases and keeps runs of letters
    and digits, so "INC-2026-Q3-011" becomes ["inc", "2026", "q3", "011"] — not the single
    token the notes show. It still works, for an instructive reason: "inc", "2026" and
    "q3" are shared with other incident IDs, so their idf is low, and "011" alone is rare.
    The ID is found by its rarest fragment.
"""

import math
import re
from collections import Counter

TOKEN = re.compile(r"[a-z0-9]+")

# Small on purpose: the words a QUESTION is made of, which say nothing about which chunk
# answers it. A long list starts removing terms that carry meaning ("not", "after").
STOPWORDS = frozenset("""
    a an the and or of to in on at for with by from as is are was were be been it its
    this that these those what which who whom when where why how did does do has have had
    happened happen about any there their they we our you your i me my can could would
""".split())


def tokenize(text: str, stopwords=frozenset()) -> list:
    return [t for t in TOKEN.findall(text.lower()) if t not in stopwords]


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75, stopwords=frozenset()):
        self.k1 = k1
        self.b = b
        self.stopwords = stopwords
        self.documents = []
        self.term_counts = []       # one Counter per document: term -> count
        self.lengths = []           # tokens per document
        self.doc_freq = Counter()   # term -> how many documents contain it

    def add_document(self, document: dict) -> None:
        terms = tokenize(document["content"], self.stopwords)
        counts = Counter(terms)
        self.documents.append(document)
        self.term_counts.append(counts)
        self.lengths.append(len(terms))
        self.doc_freq.update(counts.keys())

    def add_documents(self, documents: list) -> None:
        for document in documents:
            self.add_document(document)

    def idf(self, term: str) -> float:
        n = self.doc_freq.get(term, 0)
        return math.log(1 + (len(self.documents) - n + 0.5) / (n + 0.5))

    def search(self, query: str, k: int = 1) -> list:
        """Up to k matching documents as (document, BM25 score), best first.

        Higher is better — the opposite of VectorIndex's distance. The two numbers are on
        unrelated scales, which is exactly why 07 merges by rank, not by score.
        """
        avg_len = sum(self.lengths) / len(self.lengths)
        query_terms = tokenize(query, self.stopwords)
        scored = []
        for document, counts, length in zip(self.documents, self.term_counts, self.lengths):
            score = 0.0
            for term in query_terms:
                tf = counts.get(term, 0)
                if tf:
                    norm = self.k1 * (1 - self.b + self.b * length / avg_len)
                    score += self.idf(term) * tf * (self.k1 + 1) / (tf + norm)
            # A document sharing no term with the query is not a match at all. Ranking it
            # anyway — tied at 0, in arbitrary order — would hand it a rank, and in 07 a
            # rank is worth points. So it is left out, and the list can be shorter than k.
            if score > 0:
                scored.append((document, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]

    def __len__(self) -> int:
        return len(self.documents)
