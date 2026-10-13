"""Implementing the RAG flow.

The pipeline from the previous lesson as working code: a vector index, a similarity search
over it, and a prompt built from what the search returns.
"""

# The Five-Step RAG Implementation

# 1. Chunk the text by section
# 2. Generate embeddings for each chunk
# 3. Create a vector store and add each embedding to it
# 4. Generate an embedding for the user's question
# 5. Search the store to find the most relevant chunks

# Step 1: Chunking the Text
# First, we load our document and split it into manageable sections:

# with open("./report.md", "r") as f:
#     text = f.read()

# chunks = chunk_by_section(text)
# chunks[2]  # Test to see the table of contents

# We use the same chunk_by_section function from earlier to split our document into logical sections.

# Step 2: Generate Embeddings
# Next, we create embeddings for all our chunks at once:

# embeddings = generate_embedding(chunks)

# The embedding function has been updated to handle both single strings and lists of strings, making it more efficient for batch processing.

# Step 3: Store in Vector Database
# Now we create our vector store and populate it with embeddings and their associated text:

# store = VectorIndex()

# for embedding, chunk in zip(embeddings, chunks):
#     store.add_vector(embedding, {"content": chunk})

# Notice that we store both the embedding and the original text content. 
# This is crucial because when we search later, we need to return the actual text, not just the numerical embedding values.

# Why Store the Original Text?

# When we query our vector database, getting back just the embedding numbers isn't useful. 
# We need the actual text that was used to generate those embeddings. 
# That's why we include the original chunk text (or at least a reference to it) alongside each embedding in our database.

# Step 4: Process User Queries
# When a user asks a question, we generate an embedding for their query:

# user_embedding = generate_embedding("What did the software engineering dept do last year?")

# Step 5: Find Relevant Content
# Finally, we search our vector store to find the most similar chunks:

# results = store.search(user_embedding, 2)

# for doc, distance in results:
#     print(distance, "\n", doc["content"][0:200], "\n")

# This search returns the two most relevant chunks along with their similarity scores (cosine distances).
# The search results show us which sections of our document are most relevant to the user's question, along with similarity scores.

# Understanding the Results
# When we run our example query about the software engineering department, we get back:

# - Section 2: Software Engineering with a distance of 0.71 (closest match)
# - Methodology section with a distance of 0.72 (second closest)

# Lower distance values indicate higher similarity, so Section 2 is the most relevant to our query.

# ─────────────────────────────────────────────────────────────────────────────────────
# The course hands out VectorIndex; vector_index.py writes it out — a list and a loop, the
# same search a vector database runs, minus the index that makes it fast at scale. 07
# needs it again, so it lives outside the numbered files.
#
# Two requests to Voyage, whatever the number of questions: one batch for the chunks
# ("document"), one batch for the questions ("query"). The course embeds the question
# with the same call it used for the chunks — the "query"-for-everything default from 03.
#
# The course's own result is worth a second look: the right section at distance 0.71, the
# next at 0.72. A gap of 0.01 is a coin toss that happened to land right. What to watch in
# the output below is not just which chunk wins but the MARGIN it wins by — a small margin
# means a slightly different question could flip the answer.
#
# The course stops at retrieval, and so does this file: it builds the prompt from step 6
# of 04 and prints it, but sends nothing to Claude. Retrieval is the part that decides
# whether the answer is even possible.
# ─────────────────────────────────────────────────────────────────────────────────────

from chunking import chunk_by_section, load_report
from embeddings import embed
from vector_index import VectorIndex

QUESTIONS = [
    "What did the software engineering dept do last year?",   # the course's question
    "How many bugs did engineers fix this year?",              # "bug" is in two sections
    "What risks does the company face?",
    "How much cash does the company have?",
]


def title(chunk: str) -> str:
    return chunk.splitlines()[0].lstrip("# ").strip()


def build_prompt(question: str, results: list) -> str:
    """Step 6 from 04, with the retrieved chunks in place of the whole document."""
    context = "\n\n".join(doc["content"] for doc, _ in results)
    return (
        "Answer the user's question about the company report, using only the excerpts "
        "below. If they do not contain the answer, say so.\n\n"
        f"<user_question>\n{question}\n</user_question>\n\n"
        f"<report_excerpts>\n{context}\n</report_excerpts>"
    )


def main():
    # 1. Chunk.
    chunks = chunk_by_section(load_report())

    # 2. Embed every chunk — request 1.
    chunk_vectors = embed(chunks, input_type="document").embeddings

    # 3. Store each vector WITH its text; the vector finds the chunk, the text is the answer.
    index = VectorIndex()
    for vector, chunk in zip(chunk_vectors, chunks):
        index.add_vector(vector, {"content": chunk})
    print(f"index: {len(index)} chunks — {[title(c) for c in chunks]}\n")

    # 4. Embed every question — request 2.
    question_vectors = embed(QUESTIONS, input_type="query").embeddings

    # 5. Search.
    for question, vector in zip(QUESTIONS, question_vectors):
        results = index.search(vector, k=len(index))
        (best, best_distance), (second, second_distance) = results[0], results[1]
        print(f"> {question}")
        print(f"  1st  {best_distance:.3f}  {title(best['content'])}")
        print(f"  2nd  {second_distance:.3f}  {title(second['content'])}")
        print(f"  last {results[-1][1]:.3f}  {title(results[-1][0]['content'])}")
        print(f"  margin {second_distance - best_distance:.3f}\n")

    # 6. The prompt Claude would get for the course's question — top 2 chunks, not all six.
    top = index.search(question_vectors[1], k=2)
    prompt = build_prompt(QUESTIONS[1], top)
    print(f"prompt for {QUESTIONS[1]!r}: {len(prompt)} chars "
          f"(the whole report would be {len(load_report())})\n")
    print(prompt)


if __name__ == "__main__":
    main()
