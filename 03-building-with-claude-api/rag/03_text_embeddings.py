"""Text embeddings.

Turning a chunk of text into a vector of numbers, so that "similar meaning" becomes
"nearby vectors". Anthropic does not provide an embedding model; this is a second API.
"""

# After breaking a document into chunks, the next step in a RAG pipeline is finding which chunks are most relevant to a user's question. 
# This is essentially a search problem - you need to look through all your text chunks and identify the ones that relate to what the user is asking about.

# Semantic Search

# The most common approach for finding relevant chunks is semantic search. 
# Unlike keyword-based search that looks for exact word matches, 
# semantic search uses text embeddings to understand the meaning and context of both the user's question and each text chunk.

# Text Embeddings

# A text embedding is a numerical representation of the meaning contained in some text. 
# Think of it as converting words and sentences into a format that computers can work with mathematically.

# Here's how the process works:

# - You feed text into an embedding model
# - The model outputs a long list of numbers (the embedding)
# - Each number ranges from -1 to +1
# - These numbers represent different qualities or features of the input text

# Understanding the Numbers

# Each number in an embedding is essentially a "score" for some quality of the input text. 
# However, here's the important caveat: we don't know precisely what each number represents.
# https://everpath-course-content.s3-accelerate.amazonaws.com/instructor%2Fa46l9irobhg0f5webscixp0bs%2Fpublic%2F1748542213%2F07_-_003_-_Text_Embeddings_09.1748542213029.jpg
# While it's helpful to imagine that one number might represent "how happy the text is" or "how much the text talks about oceans," 
# these are just conceptual examples. The actual meaning of each dimension is learned by the model during training and isn't directly interpretable by humans.

# VoyageAI for Embeddings

# Since Anthropic doesn't currently provide embedding generation, the recommended provider is VoyageAI. You'll need to:
# - Sign up for a separate VoyageAI account
# - Get an API key (free to get started)
# - Add the key to your environment variables

# Implementation

# First, install the VoyageAI library:
# %pip install voyageai

# Then set up the client and create a function to generate embeddings:

# from dotenv import load_dotenv
# import voyageai

# load_dotenv()
# client = voyageai.Client()

# def generate_embedding(text, model="voyage-3-large", input_type="query"):
#     result = client.embed([text], model=model, input_type=input_type)
#     return result.embeddings[0]

# When you run this function on a text chunk, you'll get back a list of floating-point numbers representing the embedding. 
# The process is quick and straightforward 
# - the real challenge is understanding how to use these embeddings effectively in your RAG pipeline for finding the most relevant content.
# The next step is learning how to compare embeddings to determine which chunks are most similar to a user's question, 
# which forms the core of the semantic search process.


# ─────────────────────────────────────────────────────────────────────────────────────
# The client and generate_embedding() live in embeddings.py — 04 to 07 embed the same
# chunks the same way, and a numbered file cannot be imported. Two changes from the
# course version are explained there: embed() batches a whole list into one request, and
# input_type has no default, because "query" for everything is wrong for documents.
#
# Checked against the notes, measured below:
#
#   * "Each number ranges from -1 to +1" — true, and much less than it sounds. Voyage
#     vectors are normalised to length exactly 1.0, spread over 1,024 numbers, so each one
#     is tiny: about ±0.1. The length is the useful fact: it makes the dot product of two
#     vectors their cosine similarity, which is what 04 compares with.
#   * The same text embedded as "query" and as "document" gives DIFFERENT vectors. The
#     model is trained so a question lands near the passages that answer it, not near
#     text that looks like it — the two input types are the two sides of that.
#   * Embeddings are only NEARLY deterministic. One text embedded alone, twice, came back
#     identical (0.00 difference, first draft of this file). But a chunk embedded in a
#     batch differs from the same chunk embedded alone by up to ~7e-4 per number, and the
#     batched vectors themselves shifted slightly between two runs. Cosine between the
#     variants is 0.99997 — far too close to change a ranking — but it rules out ==.
#     Embed a chunk once, store the vector, compare by similarity.
#
# The key used here is a MongoDB Atlas one ("al-..."): the SDK routes it to
# ai.mongodb.com by itself. Token counts come back on every response as total_tokens.
#
# Batching is not an optimisation here, it is the only thing that works. With no payment
# method on the account, Voyage allows 3 requests a minute. The course's loop — one
# generate_embedding() per chunk — failed on the fourth chunk in the first draft of this
# file.
# ─────────────────────────────────────────────────────────────────────────────────────

from chunking import chunk_by_section, load_report
from embeddings import MODEL, cosine, embed, generate_embedding

# Three requests, no more. Without a payment method on the Voyage account the limit is 3
# requests a minute, so the course's one-call-per-chunk loop is not just slower, it fails:
# 6 chunks is 6 requests, and the fourth is refused with a RateLimitError.


def main():
    chunks = chunk_by_section(load_report())
    print(f"{len(chunks)} section chunks from report.md, model {MODEL}\n")

    # Request 1: every chunk, in one call. Index 2 is "## Software Engineering".
    batch = embed(chunks, input_type="document")
    vector = batch.embeddings[2]
    length = sum(x * x for x in vector) ** 0.5
    print(f"1. all {len(chunks)} chunks in ONE request: {len(batch.embeddings)} vectors, "
          f"{batch.total_tokens} tokens")
    print(f"   one of them ('## Software Engineering'): {len(vector)} numbers, first five "
          f"{[round(x, 4) for x in vector[:5]]}")
    print(f"   smallest {min(vector):.4f}, largest {max(vector):.4f}, length {length:.4f}")
    print(f"   one request per chunk instead: {len(chunks)} requests — at 3 a minute, "
          f"{len(chunks) / 3:.0f} minutes, and a RateLimitError on the fourth")

    # Request 2: the same chunk again, alone. Not bit-identical to its batched twin — but
    # is it close enough that batching can never change which chunk ranks first?
    alone = generate_embedding(chunks[2], input_type="document")
    drift = max(abs(a - b) for a, b in zip(vector, alone))
    print(f"\n2. the same chunk again, on its own: largest difference {drift:.2e}, "
          f"cosine {cosine(vector, alone):.6f}")
    print("   not bit-identical to the batched one — compare embeddings by similarity, "
          "never with ==")

    # Request 3: the same text, as a query.
    as_query = generate_embedding(chunks[2], input_type="query")
    print(f"\n3. the same chunk as 'query' instead of 'document': cosine "
          f"{cosine(vector, as_query):.4f}  (1.0 would mean identical)")


if __name__ == "__main__":
    main()
