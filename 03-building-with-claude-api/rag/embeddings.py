"""Embeddings — the second API, shared by every lesson from 03 onwards.

Anthropic has no embedding model, so this is Voyage AI, with its own key (VOYAGE_API_KEY
in the same .env). A key starting "al-" was issued through MongoDB Atlas; the voyageai SDK
spots the prefix and sends it to https://ai.mongodb.com/v1 instead of api.voyageai.com —
nothing to configure.

Two differences from the course's generate_embedding(), both deliberate:

  * embed() takes a LIST and makes one request for all of it. The course embeds one text
    per call; for a document of 100 chunks that is 100 requests, and on a Voyage account
    with no payment method — limited to 3 requests a minute — over half an hour. One
    batched call does the same work.
  * input_type has no default here. The course defaults it to "query" for everything,
    which quietly embeds your documents as if they were questions. Chunks are
    "document", questions are "query" — make every call say which.
"""

import os
import sys

import voyageai
from dotenv import load_dotenv

MODEL = "voyage-3-large"   # the course's; voyage-3.5 and voyage-4 also work on this key

_client = None


def get_client() -> voyageai.Client:
    """Built once, on first use — same key-check-then-construct order as helpers.py."""
    global _client
    if _client is None:
        load_dotenv()
        if not os.getenv("VOYAGE_API_KEY"):
            sys.exit("VOYAGE_API_KEY is not set. Add it to .env — see .env.example.")
        # The SDK's default is NO retries. Without a payment method on the account, Voyage
        # allows 3 requests a minute — one batch too many and the next call fails outright.
        # Retrying with backoff (1s, 2s, 4s ... capped at 16s) rides out a short burst.
        _client = voyageai.Client(max_retries=5)
    return _client


def embed(texts: list, input_type: str, model: str = MODEL):
    """One request for every text. Returns the full result: .embeddings and .total_tokens."""
    if input_type not in ("document", "query"):
        raise ValueError('input_type must be "document" (chunks) or "query" (questions)')
    return get_client().embed(texts, model=model, input_type=input_type)


def generate_embedding(text: str, input_type: str, model: str = MODEL) -> list:
    """The course's single-text version, kept for the one-off case."""
    return embed([text], input_type=input_type, model=model).embeddings[0]


def cosine(a: list, b: list) -> float:
    """Similarity of two vectors, -1 to 1. Voyage vectors are unit length, so this is just
    the dot product — but dividing by the lengths keeps it right for any vector."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b)
