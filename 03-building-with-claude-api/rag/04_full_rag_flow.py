"""The full RAG flow.

The whole pipeline end to end: chunk the documents, embed the chunks, embed the question,
find the nearest chunks, and put them in the prompt.
"""
