"""The full RAG flow.

The whole pipeline end to end: chunk the documents, embed the chunks, embed the question,
find the nearest chunks, and put them in the prompt.
"""
# This example will show you exactly how all these pieces work together to retrieve relevant information and generate responses.

# Step 1: Chunk Your Source Text

# First, we take our source document and break it into manageable chunks. For this example, we'll use two simple text sections:
# - Section 1: Medical Research - "This year saw significant strides in our understanding of XDR-47, a 'bug' we have not seen before."
# - Section 2: Software Engineering - "This division dedicated significant effort to studying various infection vectors in our distributed systems"

# Step 2: Generate Embeddings

# Next, we convert each text chunk into numerical embeddings using an embedding model. 
# To make this easier to understand, let's imagine we have a perfect embedding model that always returns exactly two numbers, 
# and we know what each number represents.

# In our imaginary model:

# - The first number represents how much the text talks about the medical field
# - The second number represents how much the text talks about software engineering
# - For the medical research section, we might get [0.97, 0.34] - very medical-focused but with some software elements due to the word "bug". 
# - For the software engineering section, we get [0.30, 0.97] - heavily software-focused but with medical undertones from "infection vectors".

# Normalization

# The embedding API typically performs a normalization step that scales each vector to have a magnitude of 1.0. 
# You don't need to worry about the math here - it's handled automatically. 
# This gives us normalized vectors like [0.944, 0.331] and [0.295, 0.955].

# Step 3: Store in Vector Database

# We store these embeddings in a vector database 
# - a specialized database optimized for storing, comparing, and searching through long lists of numbers like our embeddings.
# At this point, we pause. All the work so far has been preprocessing that happens ahead of time. 
# Now we wait for a user to submit a query.

# Step 4: Process User Query

# When a user asks a question like "I'm curious about the company. In particular, what did the software engineering dept do this year?", 
# we run their query through the same embedding model.
# This query gets embedded as something like [0.1, 0.89] - low medical score, high software engineering score. 
# After normalization, we get [0.112, 0.993].

# Step 5: Find Similar Embeddings

# We send the user's query embedding to our vector database and ask it to find the most similar stored embeddings.
# The database returns the software engineering section because it's the closest match to what the user asked about.

# How Similarity Works: Cosine Similarity

# The vector database uses cosine similarity to determine which embeddings are most similar. 
# This measures the cosine of the angle between two vectors.

# Key points about cosine similarity:

# - Results range from -1 to 1
# - Values close to 1 mean high similarity
# - Values close to -1 mean very different
# - 0 means perpendicular (no relationship)

# In our example, the cosine similarity between the user query and the software engineering chunk is 0.983 - very high similarity. 
# The similarity with the medical research chunk is only 0.398 - much lower.

# Cosine Distance

# You'll often see "cosine distance" in vector database documentation. This is simply calculated as (1 - cosine similarity). 
# With cosine distance:

# - Values close to 0 mean high similarity
# - Larger values mean less similarity
# - This adjustment makes the numbers easier to interpret in many contexts.

# Step 6: Create the Final Prompt

# Finally, we take the user's question and the most relevant text chunk we found, combine them into a prompt, and send it to Claude for a response.
# The prompt might look like:

# Answer the user's question about the financial document.

# <user_question>
# How many bugs did engineers fix this year?
# </user_question>

# <report>
# ## Section 2: Software Engineering
# This division dedicated significant effort to studying various infection vectors in our distributed systems
# </report>

# And that's the complete RAG pipeline! 
# The system successfully retrieved the most relevant information based on semantic similarity and provided it as context for generating an accurate response.



# ─────────────────────────────────────────────────────────────────────────────────────
# The course's two-number example, recomputed — no API call, just the arithmetic.
#
# Every number in the notes checks out except one. The medical chunk's similarity to the
# query is given as 0.398; it is 0.434. 0.398 is the plain dot product of the RAW vectors
# [0.1, 0.89] · [0.97, 0.34] = 0.3996 — taken before normalising. The 0.983 for the
# software chunk IS computed correctly, so the slide mixes the two calculations. The
# ranking survives either way; the numbers do not.
#
# That is the whole reason normalisation matters: on unit vectors the dot product IS the
# cosine. On raw vectors it is not, and a longer vector scores higher just for being long.
#
# Two smaller things the example glosses over:
#
#   * The question changes between steps. Step 4 embeds "what did the software
#     engineering dept do this year?"; the prompt in step 6 asks "How many bugs did
#     engineers fix this year?" — and the chunk it retrieved, about "infection vectors",
#     contains no bug count. Claude could only say the report does not say. That is the
#     "included chunks might not contain all the context" challenge from 01, live.
#   * The prompt still says "the financial document", left over from 01's example.
# ─────────────────────────────────────────────────────────────────────────────────────

from embeddings import cosine


def normalise(vector):
    length = sum(x * x for x in vector) ** 0.5
    return [x / length for x in vector]


def main():
    medical = [0.97, 0.34]
    software = [0.30, 0.97]
    query = [0.10, 0.89]

    print("normalised (the notes give [0.944, 0.331], [0.295, 0.955], [0.112, 0.993]):")
    for name, vector in [("medical", medical), ("software", software), ("query", query)]:
        print(f"  {name:9} {[round(x, 3) for x in normalise(vector)]}")

    print("\nquery vs each chunk:")
    print(f"  {'chunk':9} {'cosine':>7} {'distance':>9} {'raw dot':>8}   notes say")
    for name, vector, claimed in [("software", software, 0.983), ("medical", medical, 0.398)]:
        similarity = cosine(query, vector)
        raw_dot = sum(a * b for a, b in zip(query, vector))
        print(f"  {name:9} {similarity:>7.3f} {1 - similarity:>9.3f} {raw_dot:>8.3f}   "
              f"{claimed}{'' if abs(similarity - claimed) < 0.002 else '  ← wrong'}")

    print("\nnearest chunk:", "software" if cosine(query, software) > cosine(query, medical)
          else "medical")


if __name__ == "__main__":
    main()
