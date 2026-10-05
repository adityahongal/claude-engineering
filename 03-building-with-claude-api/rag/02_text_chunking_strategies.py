"""Text chunking strategies.

Splitting documents into pieces small enough to retrieve one at a time — by size, by
sentence, or by structure. Where the cuts fall decides what retrieval can ever find.
"""

# Text chunking is one of the most critical steps in building a RAG (Retrieval Augmented Generation) pipeline. 
# How you break up your documents directly impacts the quality of your entire system. 
# A poor chunking strategy can lead to irrelevant context being inserted into your prompts,causing your AI to give completely wrong answers.

# Consider this example: you have a document with sections on medical research and software engineering. 
# If you chunk poorly, a user asking "How many bugs did engineers fix this year?" might get information about medical research instead of software engineering,
# simply because the medical section happened to contain the word "bug" in a different context.
# This is why choosing the right chunking strategy matters so much. 

# Let's explore three main approaches.

# Size-Based Chunking

# Size-based chunking is the simplest approach - you divide your text into strings of equal length. 
# If you have a 325-character document, you might split it into three chunks of roughly 108 characters each.

# This method is easy to implement and works with any type of document, but it has clear downsides:
# - Words get cut off mid-sentence
# - Chunks lose important context from surrounding text
# - Section headers might be separated from their content

# To address these issues, you can add overlap between chunks. 
# This means each chunk includes some characters from the neighboring chunks, providing better context and ensuring complete words and sentences.
# Here's a basic implementation:

# def chunk_by_char(text, chunk_size=150, chunk_overlap=20):
#     chunks = []
#     start_idx = 0
    
#     while start_idx < len(text):
#         end_idx = min(start_idx + chunk_size, len(text))
#         chunk_text = text[start_idx:end_idx]
#         chunks.append(chunk_text)
        
#         start_idx = (
#             end_idx - chunk_overlap if end_idx < len(text) else len(text)
#         )
    
#     return chunks

# Structure-Based Chunking

# Structure-based chunking divides text based on the document's natural structure - headers, paragraphs, and sections. 
# This works great when you have well-formatted documents like Markdown files.
# For a Markdown document, you can split on header markers:

# def chunk_by_section(document_text):
#     pattern = r"\n## "
#     return re.split(pattern, document_text)

# This approach gives you the cleanest, most meaningful chunks because each one represents a complete section. 
# However, it only works when you have guarantees about your document structure. 
# Many real-world documents are plain text or PDFs without clear structural markers.

# Semantic-Based Chunking

# Semantic-based chunking is the most sophisticated approach. 
# You divide text into sentences, then use natural language processing to determine how related consecutive sentences are. 
# You build chunks from groups of related sentences.
# This method is computationally expensive but produces the most relevant chunks.
# It requires understanding the meaning of individual sentences and is more complex to implement than the other strategies.

# Sentence-Based Chunking

# A practical middle ground is chunking by sentences. 
# You split the text into individual sentences using regular expressions, then group them into chunks with optional overlap:

# def chunk_by_sentence(text, max_sentences_per_chunk=5, overlap_sentences=1):
#     sentences = re.split(r"(?<=[.!?])\s+", text)
    
#     chunks = []
#     start_idx = 0
    
#     while start_idx < len(sentences):
#         end_idx = min(start_idx + max_sentences_per_chunk, len(sentences))
#         current_chunk = sentences[start_idx:end_idx]
#         chunks.append(" ".join(current_chunk))
        
#         start_idx += max_sentences_per_chunk - overlap_sentences
        
#         if start_idx < 0:
#             start_idx = 0
    
#     return chunks

# Choosing Your Strategy

# Your choice depends entirely on your use case and document guarantees:

# - Structure-based: Best results when you control document formatting (like internal company reports)
# - Sentence-based: Good middle ground for most text documents
# - Size-based: Most reliable fallback that works with any content type, including code

# Size-based chunking with overlap is often the go-to choice in production because it's simple, reliable, and works with any document type.
# While it may not give perfect results, it consistently produces reasonable chunks that won't break your pipeline.

# ─────────────────────────────────────────────────────────────────────────────────────
# The three chunkers live in chunking.py, not here — 03 to 07 chunk the same document the
# same way, and a numbered file cannot be imported. report.md is that document: a small
# annual review with the notes' example built in. "bug" means a stomach bug in Medical
# Research and a software defect in Software Engineering, so a chunk that straddles the two
# is exactly the "wrong context" failure the notes open with.
#
# Two of the course functions have bugs, fixed in chunking.py:
#
#   * chunk_by_sentence emits a duplicate tail: 5 sentences, 5 per chunk, overlap 1 gives
#     ['A. B. C. D. E.', 'E.'] — the second chunk is a subset of the first, and costs a
#     retrieval slot for nothing.
#   * both loops run forever when the overlap is >= the chunk size: the start index never
#     moves forward. The fixed versions refuse that input instead.
#
# And chunk_by_section's re.split(r"\n## ") eats the "## " from every header after the
# first. Harmless to read, but the header is the most useful line for retrieval to match
# on; a lookahead split keeps it.
#
# One claim in the notes does not survive measurement: overlap does NOT ensure "complete
# words and sentences". It copies the last N characters of a chunk into the next one, and
# those N characters start wherever the arithmetic says — mid-word as often as not. What
# overlap buys is that a sentence cut at a boundary appears WHOLE in at least one of the
# two chunks, as long as it is shorter than the overlap. The count below shows the cuts.
#
# Semantic chunking is described but not built: grouping sentences by meaning needs
# embeddings, which arrive in 03.
# ─────────────────────────────────────────────────────────────────────────────────────

from chunking import chunk_by_char, chunk_by_section, chunk_by_sentence, load_report


def mid_word_cuts(text: str, chunks: list) -> int:
    """Chunk edges that land inside a word. Only meaningful for character chunks, which are
    exact slices of the text — sentence chunks are re-joined, so they no longer are."""
    cuts = 0
    position = 0
    for chunk in chunks:
        start = text.index(chunk, position)
        end = start + len(chunk)
        if 0 < start and text[start - 1].isalnum() and text[start].isalnum():
            cuts += 1
        if end < len(text) and text[end - 1].isalnum() and text[end].isalnum():
            cuts += 1
        position = start + 1
    return cuts


def spans_sections(chunk: str) -> bool:
    """True if a section header starts anywhere but the very top of the chunk — i.e. the
    chunk carries the end of one section and the start of another."""
    return chunk.find("## ", 1) != -1


def one_line(chunk: str, width: int = 88) -> str:
    flat = " ".join(chunk.split())
    return flat if len(flat) <= width else flat[:width - 3] + "..."


def main():
    text = load_report()
    strategies = {
        "size (150 chars, 20 overlap)": chunk_by_char(text),
        "sentence (5 per chunk, 1 overlap)": chunk_by_sentence(text),
        "section (## headers)": chunk_by_section(text),
    }

    print(f"report.md: {len(text)} characters\n")
    print(f"{'strategy':36} {'chunks':>6} {'min':>5} {'max':>5} {'mid-word':>9} {'span 2+':>8}")
    for name, chunks in strategies.items():
        sizes = [len(c) for c in chunks]
        cuts = mid_word_cuts(text, chunks) if name.startswith("size") else "-"
        spanning = sum(spans_sections(c) for c in chunks)
        print(f"{name:36} {len(chunks):>6} {min(sizes):>5} {max(sizes):>5} "
              f"{cuts:>9} {spanning:>8}")

    # The notes' failure, made concrete: which chunks would a search for "bug" match, and
    # what else comes along with them?
    for name, chunks in strategies.items():
        print(f"\n── chunks containing 'bug' — {name}")
        for i, chunk in enumerate(chunks):
            if "bug" in chunk.lower():
                flag = "  [SPANS SECTIONS]" if spans_sections(chunk) else ""
                print(f"  #{i:<2} {one_line(chunk)}{flag}")

    # The naive sentence regex, caught in the act.
    sentences = chunk_by_sentence(text, max_sentences_per_chunk=1, overlap_sentences=0)
    false_ends = [s for s in sentences if s.endswith(("Dr.", "e.g."))]
    print(f"\nsentence split, false sentence ends: {[one_line(s, 40) for s in false_ends]}")


if __name__ == "__main__":
    main()
