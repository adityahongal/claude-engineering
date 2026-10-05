"""The chunkers — shared by every lesson from 02 onwards.

The course's three functions, with the bugs fixed. A numbered lesson file cannot be
imported, and 03–07 all need to chunk the same document the same way, so they live here.

What changed from the course versions, and why:

    chunk_by_char       refuses an overlap >= chunk_size. The course's loop moves its start
                        back by `overlap` each time; at overlap >= size it never moves
                        forward, and loops forever.
    chunk_by_sentence   stops once a chunk reaches the last sentence. The course's loop
                        keeps going and emits a trailing chunk that is a SUBSET of the one
                        before it — 5 sentences, 5 per chunk, overlap 1 gives
                        ['A. B. C. D. E.', 'E.'].
                        Same infinite-loop guard as above.
    chunk_by_section    splits BEFORE each header instead of ON it. re.split(r"\\n## ")
                        consumes the "## ", so every chunk after the first loses the marker
                        that says it is a header.
"""

import re
from pathlib import Path

REPORT = Path(__file__).parent / "report.md"


def load_report() -> str:
    return REPORT.read_text()


def chunk_by_char(text: str, chunk_size: int = 150, chunk_overlap: int = 20) -> list:
    """Fixed-size windows; each one repeats the last `chunk_overlap` chars of the one before."""
    if not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_overlap must be at least 0 and smaller than chunk_size")

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - chunk_overlap
    return chunks


# Split after . ! or ? followed by whitespace. Naive on purpose — it is the course's — and
# it shows: "Dr. Okafor" and "e.g. on" both end a "sentence" here.
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def chunk_by_sentence(text: str, max_sentences_per_chunk: int = 5,
                      overlap_sentences: int = 1) -> list:
    """Groups of whole sentences; each one repeats the last `overlap_sentences` before it."""
    if not 0 <= overlap_sentences < max_sentences_per_chunk:
        raise ValueError(
            "overlap_sentences must be at least 0 and smaller than max_sentences_per_chunk"
        )

    sentences = SENTENCE_END.split(text.strip())
    chunks = []
    start = 0
    while start < len(sentences):
        end = min(start + max_sentences_per_chunk, len(sentences))
        chunks.append(" ".join(sentences[start:end]))
        if end == len(sentences):
            break   # the course keeps going here, and repeats the tail as its own chunk
        start = end - overlap_sentences
    return chunks


def chunk_by_section(text: str) -> list:
    """One chunk per "## " section, header included; anything before the first is its own."""
    # (?=...) is a lookahead: split at the position BEFORE "## ", consuming nothing, so the
    # header stays at the top of its chunk.
    return [part.strip() for part in re.split(r"\n(?=## )", text) if part.strip()]
