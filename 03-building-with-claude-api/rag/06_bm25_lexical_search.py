"""BM25 lexical search.

Ranking by the words a chunk actually contains rather than by meaning. Catches what
embeddings miss — exact identifiers, error codes, rare terms.
"""

# When building RAG pipelines, you'll quickly discover that semantic search alone doesn't always return the best results. 
# Sometimes you need exact term matches that semantic search might miss. 
# The solution is to combine semantic search with lexical search using a technique called BM25.

# The Problem with Semantic Search Alone

# Let's say you're searching for a specific incident ID like "INC-2023-Q4-011" in a document. 
# While semantic search excels at understanding context and meaning, 
# it might return sections that are semantically related but don't actually contain the exact term you're looking for.
# In the example above, semantic search returned the cybersecurity section (which does contain the incident ID) 
# but also returned a financial analysis section that doesn't mention the incident at all. 
# This happens because semantic search focuses on conceptual similarity rather than exact term matching.

# Hybrid Search Strategy

# The solution is to run both semantic and lexical searches in parallel, then merge the results. 
# This gives you the best of both worlds

# - Semantic search finds conceptually related content using embeddings
# - Lexical search finds exact term matches using classic text search
# - Merged results combine both approaches for better accuracy

# How BM25 Works

# BM25 (Best Match 25) is a popular algorithm for lexical search in RAG systems. 
# Here's how it processes a search query:

# Step 1: Tokenize the query
# Break the user's question into individual terms. For example, "a INC-2023-Q4-011" becomes ["a", "INC-2023-Q4-011"].

# Step 2: Count term frequency
# See how often each term appears across all your documents. Common words like "a" might appear 5 times, while specific terms like "INC-2023-Q4-011" might appear only once.

# Step 3: Weight terms by importance
# Terms that appear less frequently get higher importance scores. The word "a" gets low importance because it's common, while "INC-2023-Q4-011" gets high importance because it's rare.

# Step 4: Find best matches
# Return documents that contain more instances of the higher-weighted terms.

# Implementing BM25 Search
# Here's how to set up a basic BM25 search system:

# # 1. Chunk your text by sections
# chunks = chunk_by_section(text)

# # 2. Create a BM25 store and add documents
# store = BM25Index()
# for chunk in chunks:
#     store.add_document({"content": chunk})

# # 3. Search the store
# results = store.search("What happened with INC-2023-Q4-011?", 3)

# # Print results
# for doc, distance in results:
#     print(distance, "\n", doc["content"][:200], "\n----\n")

# When you run this search, you'll get much better results than semantic search alone. 
# The BM25 algorithm prioritizes sections that actually contain your specific search terms, especially rare terms like incident IDs.

# Why This Works Better
# BM25 excels at finding exact matches because it:

# - Gives higher weight to rare, specific terms
# - Ignores common words that don't add search value
# - Focuses on term frequency rather than semantic meaning
# - Works especially well for technical terms, IDs, and specific phrases
    
# The key insight is that both search methods have complementary strengths. 
# Semantic search understands context and meaning, while lexical search ensures you don't miss exact term matches. 
# By combining them, you create a more robust search system that handles both conceptual queries and specific lookups effectively.

# In the next step, you'll learn how to merge results from both search systems to create a unified hybrid search experience.

# ─────────────────────────────────────────────────────────────────────────────────────
# BM25Index lives in bm25_index.py — 07 runs it beside VectorIndex. The formula, and what
# k1 and b do, are written out at the top of that file.
#
# report.md has no IDs in it, so this lesson adds a second document: incidents.md, an
# incident log whose IDs differ by a few characters (INC-2026-Q3-007 vs INC-2026-Q3-011).
# Both documents go into the same index — RAG over more than one document, which 01 listed
# as a benefit and nothing had tested yet.
#
# Two claims in the notes do not hold up here, measured below:
#
#   * "INC-2023-Q4-011" does not stay one token. The tokenizer keeps runs of letters and
#     digits, so the ID becomes ["inc", "2026", "q3", "011"]. Most tokenizers do the
#     same. It works anyway because three of the four pieces are shared with other IDs —
#     low idf — and "011" is not: the ID is found by its rarest fragment.
#   * BM25 does not "ignore common words". It down-weights words by how common they are
#     IN THIS COLLECTION, and in 11 chunks, "what" and "happened" each appear once — as
#     rare as "011". The incident log's intro, which I wrote as "each entry records what
#     happened", outranked the incident itself. A short stopword list fixes it; so,
#     differently, does 07's fusion with semantic search.
#
# And the reverse case, where lexical search is the one that fails: a question that
# shares MEANING with the answer but not words. "lose money because of a software
# mistake" never says "rounding", "invoice" or "overcharged".
# ─────────────────────────────────────────────────────────────────────────────────────

from bm25_index import STOPWORDS, BM25Index, tokenize
from chunking import chunk_by_section, load_incidents, load_report
from embeddings import embed
from vector_index import VectorIndex

QUESTIONS = [
    "What happened with INC-2026-Q3-011?",                         # an exact ID
    "Did the company lose money because of a software mistake?",   # meaning, no shared words
]


def title(document: dict) -> str:
    return document["content"].splitlines()[0].lstrip("# ").strip()


def show(label: str, results: list, number: str) -> None:
    print(f"  {label}")
    for rank, (document, value) in enumerate(results, 1):
        print(f"    {rank}. {number} {value:6.3f}  {title(document)}")


def main():
    documents = [{"content": chunk} for chunk in
                 chunk_by_section(load_report()) + chunk_by_section(load_incidents())]
    print(f"{len(documents)} chunks from report.md + incidents.md\n")

    plain = BM25Index()
    plain.add_documents(documents)
    filtered = BM25Index(stopwords=STOPWORDS)
    filtered.add_documents(documents)

    # Semantic, for comparison: one request for the chunks, one for both questions.
    vectors = VectorIndex()
    vectors.add_documents(documents)
    question_vectors = embed(QUESTIONS, input_type="query").embeddings

    print(f"tokens: {tokenize(QUESTIONS[0])}")
    print("idf:    " + ", ".join(f"{t}={plain.idf(t):.2f}"
                                 for t in tokenize(QUESTIONS[0])))

    for question, vector in zip(QUESTIONS, question_vectors):
        print(f"\n> {question}")
        show("BM25", plain.search(question, 3), "score")
        show("BM25, stopwords removed", filtered.search(question, 3), "score")
        show("semantic", vectors.search(vector, 3), "dist ")


if __name__ == "__main__":
    main()
