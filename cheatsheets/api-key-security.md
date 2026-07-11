# API Key Security — Cheatsheet

**The rule:** NEVER put your Claude API key in frontend / browser / React code.

**Why:** Anything in browser code is visible to anyone who opens DevTools. An exposed
key lets strangers make API calls billed to your account.

**The correct pattern:**

```
React frontend  →  your backend (Node/Express/serverless)  →  Claude API
                        ↑ API key lives here, never leaves the server
```

- Your React app calls **your own backend**.
- Your backend holds the key (in an environment variable) and calls Claude.
- The key never reaches the browser.

**How to store the key:**
- Put it in an environment variable: `ANTHROPIC_API_KEY` (never hardcode it in a file).
- The SDK reads it automatically: `new Anthropic()` picks up `ANTHROPIC_API_KEY`.
- Add `.env` to `.gitignore` so the key never gets committed to GitHub.

**Frontend analogy:** treat the API key like a database password — it belongs on the
server, not in the client bundle. Same reason you don't ship DB credentials to the browser.
