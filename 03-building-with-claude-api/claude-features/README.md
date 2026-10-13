# Features of Claude

What the Messages API can do beyond plain text in and text out: reasoning before
answering, reading images and PDFs, citing its sources, caching long prompts, and running
code. Each lesson adds one capability to the same request shape — usually a new content
block on the way in, or a new block type on the way out.

## Files

- `01_extended_thinking.py` — reasoning before answering, and the thinking blocks it returns
- `02_image_support.py` — images as content blocks, by base64 or URL
- `03_pdf_support.py` — whole PDFs as document blocks
- `04_citations.py` — answers tied to the exact passages they came from
- `05_prompt_caching.py` — reusing a long, unchanging prompt prefix across requests
- `06_rules_of_prompt_caching.py` — breakpoints, minimum length, lifetime, and what breaks a cache
- `07_prompt_caching_in_action.py` — a real cached request, proved from the usage numbers
- `08_code_execution_and_files_api.py` — server-side code execution, and files uploaded once

Lesson files are numbered so the folder reads in course order. Shared code comes from the
`claude_course` package — `from claude_course import get_client, run, chat, UsageTracker`
— rather than a local `helpers.py`; see the [module README](../README.md).

The course closes the module with a quiz, which produces no file.

## Run

```bash
cd 03-building-with-claude-api/claude-features
python 01_extended_thinking.py
```

The virtual environment and `.env` are shared — see the [module README](../README.md#setup).
