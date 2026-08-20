// hello-claude.mjs — my first Claude API call
// STATUS: written & understood, NOT YET RUN (waiting on API credits).
//
// Run later with:
//   npm init -y
//   npm install @anthropic-ai/sdk
//   export ANTHROPIC_API_KEY="sk-ant-..."
//   node hello-claude.mjs

import Anthropic from "@anthropic-ai/sdk";

// Reads the key from the ANTHROPIC_API_KEY environment variable.
// Never hardcode the key here — and never run this in browser/React code.
const client = new Anthropic();

const message = await client.messages.create({
  model: "claude-haiku-4-5",   // cheapest tier — swap for claude-opus-5 when quality matters
  max_tokens: 1024,            // cap on the reply length (required)
  messages: [
    { role: "user", content: "Hello, Claude! Say hi in one sentence." },
  ],
});

// The response is an array of content blocks; the text lives in the first one.
console.log(message.content[0].text);
