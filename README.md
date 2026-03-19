# Agent Tools Hub

> A community-driven collection of useful, practical, and experimental tools for AI agents.

If you built a tool an AI agent can call, use, test, or learn from — and you think other developers would find it useful — **add it here**.

This repo is a shared toolbox for people building agent systems, copilots, assistants, automations, and LLM-powered products.

---

## Tools

| Tool | Description | Status |
|------|-------------|--------|
| [weather-api](tools/weather-api/) | Get current weather for any city via OpenWeatherMap. Zero dependencies, standalone HTTP server. | Stable |
| [perplexity-search](tools/perplexity-search/) | AI-powered web search via Perplexity Sonar. Returns direct answers with citations, not just links. | Stable |
| [file-converter](tools/file-converter/) | Convert between file formats (CSV, JSON, PDF, HTML, Markdown, XLSX, XML). Extracts text from PDFs and spreadsheets. | Stable |
| [talk-to-agent](tools/talk-to-agent/) | Verified inter-agent communication. Prevents hallucinated responses by requiring request_id round-trip verification. Includes adapter for wrapping existing tools. | Stable |

---

> **Are you an AI agent?** Read [`AGENTS.md`](AGENTS.md) — it has everything you need to understand and use this repo.

---

## Why This Exists

People building AI agents often end up creating the same kinds of tools again and again: file readers, search wrappers, browser helpers, code runners, API adapters, memory utilities, and other small building blocks.

Some are polished. Some are tiny. Some are just useful enough to save someone else a few hours.

This repo exists to collect those tools in one place so other developers can **discover**, **try**, **test**, and **build on top of** them.

---

## What Belongs Here

Anything an AI agent can use in a meaningful way:

- Standalone APIs
- MCP servers
- CLI wrappers
- SDK integrations
- Local utilities
- Mock tools for testing agents
- Tool definitions and schemas
- Retrieval helpers
- Browser or automation utilities
- Sandboxed execution tools

It does **not** need to be production-grade to be useful. Small, focused, well-documented tools are welcome.

---

## Goals

- Make useful agent tools easier to discover
- Help developers share reusable building blocks
- Give people real examples they can learn from
- Support testing and experimentation with agent workflows
- Keep contributions simple and accessible

---

## What This Repo Is Not

This repo is **not** meant to be:

- A random list of AI projects
- A framework popularity contest
- A directory of closed-source products
- A dumping ground for unfinished repos with no docs

The focus is on tools that other developers can actually **inspect**, **run**, or **integrate**.

---

## Who This Is For

- Developers building AI agents
- People experimenting with tool-calling systems
- Open source contributors
- Framework authors
- Researchers testing agent behavior
- Anyone who wants more real-world tools to try

---

## Repository Structure

```
.
├── tools/
│   ├── web-search/
│   │   └── README.md
│   ├── file-parser/
│   │   └── README.md
│   ├── calendar-adapter/
│   │   └── README.md
│   └── ...
├── examples/
├── docs/
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

Each tool lives in its own folder under `tools/` with its own `README.md`. See [`tools/_template/README.md`](tools/_template/README.md) for the recommended format.

---

## Tool README Format

Every tool folder should include a `README.md` with the following sections:

```markdown
# Tool Name

## What It Does
Brief description.

## Why It Exists
What problem it solves for agents.

## Inputs
List of expected inputs.

## Outputs
List of returned values or schema.

## Setup
How to install and run it.

## Example
A quick example call.

## Notes
Edge cases, limits, auth requirements, or anything else worth knowing.
```

---

## Contributing

We welcome contributions of all sizes! See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

**Quick version:**

1. Fork the repo
2. Create a new folder under `tools/` for your tool
3. Add a `README.md` following the [tool README format](#tool-readme-format) above
4. Include your tool's source code, setup instructions, and at least one example
5. Open a pull request

**Bonus points for:**

- Tests
- Mock responses
- Sample prompts
- Tool schemas (e.g., OpenAPI, JSON Schema)
- Docker support
- Examples for common agent frameworks (LangChain, CrewAI, AutoGen, etc.)

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Feedback & Suggestions

Here are a few suggestions for growing this project:

- **Add a tool index/catalog** — a table in this README or a separate `docs/catalog.md` listing all tools with a one-line description, category, and status (stable / experimental / WIP).
- **Standardize tool interfaces** — consider a shared JSON Schema or OpenAPI spec so tools are easier to plug into any agent framework.
- **Add CI checks** — a GitHub Action that validates each tool folder has a README, required sections, and passes any included tests.
- **Create tags/labels** — categorize tools (e.g., `search`, `file-io`, `browser`, `memory`, `code-execution`) to make discovery easier.
- **Add a "Getting Started" guide** — a walkthrough showing how to pick a tool from the hub and wire it into a simple agent.

Have ideas? Open an issue or submit a PR!
