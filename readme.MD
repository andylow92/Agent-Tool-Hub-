Agent Tools Hub

A community repo for useful, practical, and experimental tools for AI agents.

The goal is simple: if you built a tool an AI agent can call, use, test, or learn from — and you think other developers would find it useful — add it here.

This repo is a shared toolbox for people building agent systems, copilots, assistants, automations, and LLM-powered products.

Why this exists

People building AI agents often end up creating the same kinds of tools again and again: file readers, search wrappers, browser helpers, code runners, API adapters, memory utilities, and other small building blocks.

Some are polished. Some are tiny. Some are just useful enough to save someone else a few hours.

This repo exists to collect those tools in one place so other developers can discover them, try them, test them, and build on top of them.

What belongs here

Anything an AI agent can use in a meaningful way.

Examples:

Standalone APIs

MCP servers

CLI wrappers

SDK integrations

Local utilities

Mock tools for testing agents

Tool definitions and schemas

Retrieval helpers

Browser or automation utilities

Sandboxed execution tools

It does not need to be production-grade to be useful. Small, focused, well-documented tools are welcome.

Goals

Make useful agent tools easier to discover

Help developers share reusable building blocks

Give people real examples they can learn from

Support testing and experimentation with agent workflows

Keep contributions simple and accessible

What this repo is not

This repo is not meant to be:

A random list of AI projects

A framework popularity contest

A directory of closed-source products

A dumping ground for unfinished repos with no docs

The focus is on tools that other developers can actually inspect, run, or integrate.

Who this is for

Developers building AI agents

People experimenting with tool-calling systems

Open source contributors

Framework authors

Researchers testing agent behavior

Anyone who wants more real-world tools to try

Repository structure

A simple structure like this works well:

.
├── tools/
│   ├── web-search/
│   ├── file-parser/
│   ├── calendar-adapter/
│   └── ...
├── examples/
├── docs/
└── README.md

Each tool should ideally live in its own folder with a short README.

What to include in a contribution

A good contribution usually includes:

A short description of what the tool does

The problem it solves

Input and output format

How an agent is expected to call it

Setup instructions

Example usage

Limitations or edge cases

License information

Bonus points for:

Tests

Mock responses

Sample prompts

Tool schemas

Docker support

Examples for common agent frameworks
