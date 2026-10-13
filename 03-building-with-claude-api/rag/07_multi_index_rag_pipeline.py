"""A Multi-Index RAG pipeline.

Running semantic and lexical search side by side and merging their rankings into one
list, so each covers what the other misses.
"""

# We've built separate implementations for semantic search (using vector embeddings) and lexical search (using BM25). 
# Now it's time to combine them into a unified search pipeline that leverages the strengths of both approaches.

# The Multi-Index Architecture

# Both our VectorIndex and BM25Index classes share nearly identical APIs - they both have add_document() and search() methods. 
# This consistency makes it straightforward to wrap them together in a new class called Retriever.
# The Retriever acts as a coordinator that forwards user queries to both indexes, collects their results, and merges them using a technique called reciprocal rank fusion.

# Understanding Reciprocal Rank Fusion

# Merging results from different search methods isn't as simple as just concatenating lists. 
# Each method uses different scoring systems, so we need a way to normalize and combine their rankings fairly.
# Here's how reciprocal rank fusion works with an example. Let's say we search for information about "INC-2023-Q4-011" and get these results:

# - VectorIndex returns: Section 2 (rank 1), Section 7 (rank 2), Section 6 (rank 3)
# - BM25Index returns: Section 6 (rank 1), Section 2 (rank 2), Section 7 (rank 3)

# We combine these into a single table showing each text chunk's rank from both indexes, then apply the RRF formula:

# RRF_score(d) = Σ(1 / (k + rank_i(d)))

# Where k is a constant (often 60, but we'll use 1 for clearer results) and rank_i(d) is the rank of document d in the i-th ranking.
# For our example:

# - Section 2: 1.0/(1+1) + 1.0/(1+2) = 0.833
# - Section 7: 1.0/(1+2) + 1.0/(1+3) = 0.583
# - Section 6: 1.0/(1+3) + 1.0/(1+1) = 0.75

# The final ranking becomes: Section 2 (0.833), Section 6 (0.75), Section 7 (0.583). 
# This makes intuitive sense - Section 2 performed well in both indexes, so it rises to the top.

# Implementation Details
# The Retriever class wraps multiple search indexes and provides a unified interface:

# class Retriever:
#     def __init__(self, *indexes: SearchIndex):
#         if len(indexes) == 0:
#             raise ValueError("At least one index must be provided")
#         self._indexes = list(indexes)
    
#     def add_document(self, document: Dict[str, Any]):
#         for index in self._indexes:
#             index.add_document(document)
    
#     def search(self, query_text: str, k: int = 1, k_rrf: int = 60):
#         # Get results from all indexes
#         all_results = []
#         for idx, results in enumerate(all_results):
#             for rank, (doc, _) in enumerate(results):
                # Track document ranks across indexes
                # Apply RRF scoring formula
        # Return merged and sorted results

# The key insight is that by maintaining consistent APIs across different search implementations, we can easily combine them without tight coupling.

# Testing the Hybrid Approach

# Remember our earlier problem where searching for "what happened with INC-2023-Q4-011?" returned unexpected results from the vector-only approach? 
# The cybersecurity incident (Section 10) came first, but financial analysis (Section 3) came second instead of the more relevant software engineering section.

# With our hybrid retriever, we now get much better results:

# Section 10: Cybersecurity Analysis - Incident Response Report (most relevant)
# Section 2: Software Engineering - Project Phoenix Stability Enhancements (second most relevant)
# Section 5: Legal Developments (third)

# This demonstrates how combining semantic and lexical search can overcome the limitations of either approach used alone.

# Extensibility

# The beauty of this architecture is its extensibility. 
# Since all indexes implement the same SearchIndex protocol with add_document() and search() methods, you can easily add new search methodologies:
# Want to add a keyword-based index? A graph-based search? A specialized domain index? 
# Just implement the same interface and the Retriever will automatically incorporate it into the fusion process.
# This modular approach keeps each search implementation focused and testable while providing a clean way to combine their strengths in the final system.


# ─────────────────────────────────────────────────────────────────────────────────────
# The notes' Retriever is a sketch — its search() loops over an empty list. Written out
# below, with the merge split into its own function, fuse(), so the same per-index
# rankings can be fused twice (k_rrf = 1 and 60) without searching, and paying Voyage,
# twice.
#
# The RRF arithmetic in the notes is right: 0.833, 0.75 and 0.583 all check out, and the
# first thing main() does is recompute them.
#
# What RRF throws away, deliberately: the scores. A cosine distance and a BM25 score are
# on unrelated scales — 0.57 "distance" and 5.6 "score" cannot be added or compared — so
# only the POSITION in each list counts. The price is that RRF cannot tell a confident
# first place from a lucky one: an index that is sure and an index that is lost both hand
# their rank 1 the same 1/(k + 1).
#
# k_rrf: with k = 1, rank 1 is worth 0.5 and rank 2 is worth 0.33 — the top of each list
# dominates. With k = 60 (the usual default), rank 1 is 0.0164 and rank 2 0.0161, so
# appearing in BOTH lists matters far more than where. The notes use 1 for readable
# numbers; the measurement below shows whether it changes the answer.
#
# MEASURED, and the opposite of the notes' conclusion: on the meaning question, fusion
# made retrieval WORSE. Semantic search alone ranks the invoice error first. BM25 does not
# match it at all (no shared words), so it scores only 1/(k + 1) from one list — while a
# chunk that is mediocre in BOTH lists (Software Engineering: 3rd and 4th) collects two
# contributions and wins. At k = 1 it is worse still: Outlook, BM25's first and
# semantic's LAST of 11, comes out on top. RRF rewards agreement, so an index that is
# confidently lost drags the fused answer with it. Hybrid search is not free accuracy;
# the usual mitigations are weighting the indexes, fusing only each index's top few, or
# dropping an index's results below a score threshold.
#
# Interfaces: VectorIndex gained add_documents() and search("text") for this — it embeds
# for itself now, in one batched request — and BM25Index already had them. The
# Retriever never learns which index is which.
# ─────────────────────────────────────────────────────────────────────────────────────

from collections import defaultdict
from typing import Protocol

from bm25_index import STOPWORDS, BM25Index
from chunking import chunk_by_section, load_incidents, load_report
from vector_index import VectorIndex


class SearchIndex(Protocol):
    """What the Retriever needs from an index — nothing more."""

    def add_documents(self, documents: list) -> None: ...
    def search(self, query: str, k: int = 1) -> list: ...


def fuse(rankings: list, k_rrf: int = 60) -> list:
    """Reciprocal rank fusion: one ranked list of (document, score) out of several.

    Each list contributes 1 / (k_rrf + rank) to every document in it, rank counted from 1.
    A document missing from a list gets nothing from that list.
    """
    scores = defaultdict(float)
    by_id = {}
    for ranking in rankings:
        for rank, (document, _) in enumerate(ranking, 1):
            # id(), not the text: the indexes were handed the SAME dict objects, so
            # identity is exactly "the same chunk", even if two chunks had equal text.
            scores[id(document)] += 1 / (k_rrf + rank)
            by_id[id(document)] = document
    fused = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    return [(by_id[doc_id], score) for doc_id, score in fused]


class Retriever:
    def __init__(self, *indexes: SearchIndex):
        if not indexes:
            raise ValueError("At least one index must be provided")
        self.indexes = list(indexes)

    def add_documents(self, documents: list) -> None:
        for index in self.indexes:
            index.add_documents(documents)

    def rankings(self, query: str) -> list:
        """Every index's FULL ranking — fusion needs ranks beyond the final k to be fair."""
        return [index.search(query, k=len(index)) for index in self.indexes]

    def search(self, query: str, k: int = 1, k_rrf: int = 60) -> list:
        return fuse(self.rankings(query), k_rrf)[:k]


QUESTIONS = [
    "What happened with INC-2026-Q3-011?",
    "Did the company lose money because of a software mistake?",
]


def title(document: dict) -> str:
    return document["content"].splitlines()[0].lstrip("# ").strip()


def rank_of(document: dict, ranking: list) -> str:
    for rank, (candidate, _) in enumerate(ranking, 1):
        if candidate is document:
            return str(rank)
    return "-"


def main():
    # The notes' worked example, recomputed with the real fuse().
    s2, s6, s7 = {"content": "Section 2"}, {"content": "Section 6"}, {"content": "Section 7"}
    example = fuse([[(s2, 0), (s7, 0), (s6, 0)], [(s6, 0), (s2, 0), (s7, 0)]], k_rrf=1)
    print("notes' example, k=1: " + ", ".join(f"{d['content']} {score:.3f}"
                                              for d, score in example))
    print("                     (notes: Section 2 0.833, Section 6 0.75, Section 7 0.583)\n")

    documents = [{"content": chunk} for chunk in
                 chunk_by_section(load_report()) + chunk_by_section(load_incidents())]
    vectors = VectorIndex()
    lexical = BM25Index(stopwords=STOPWORDS)
    retriever = Retriever(vectors, lexical)
    retriever.add_documents(documents)    # one Voyage request for all 11 chunks

    for question in QUESTIONS:
        semantic, bm25 = retriever.rankings(question)    # one Voyage request
        print(f"> {question}")
        print(f"  {'chunk':44} {'semantic':>8} {'BM25':>5} {'fused k=60':>11} {'fused k=1':>10}")
        fused_60 = fuse([semantic, bm25], k_rrf=60)
        fused_1 = fuse([semantic, bm25], k_rrf=1)
        for document, _ in fused_60[:4]:
            print(f"  {title(document)[:44]:44} {rank_of(document, semantic):>8} "
                  f"{rank_of(document, bm25):>5} {rank_of(document, fused_60):>11} "
                  f"{rank_of(document, fused_1):>10}")
        best_semantic = semantic[0][0]
        print(f"  → retrieved: {title(fused_60[0][0])}")
        print(f"  semantic alone picked {title(best_semantic)!r}: BM25 rank "
              f"{rank_of(best_semantic, bm25)}, fused rank {rank_of(best_semantic, fused_60)} "
              f"(k=60) / {rank_of(best_semantic, fused_1)} (k=1)\n")


if __name__ == "__main__":
    main()
