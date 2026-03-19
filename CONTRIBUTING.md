# Contributing to Agent Tools Hub

Thanks for your interest in contributing! This project thrives on community contributions — whether it's a polished API wrapper or a small utility that saved you time.

## How to Contribute

### 1. Fork and Clone

```bash
git clone https://github.com/<your-username>/Agent-Tool-Hub-.git
cd Agent-Tool-Hub-
```

### 2. Create Your Tool Folder

Add a new folder under `tools/` with a descriptive name:

```bash
mkdir tools/your-tool-name
```

### 3. Add a README

Every tool **must** include a `README.md` with these sections:

| Section        | Description                                      |
|----------------|--------------------------------------------------|
| **What It Does**   | Brief description of the tool                |
| **Why It Exists**  | The problem it solves for agents              |
| **Inputs**         | Expected inputs (parameters, env vars, etc.) |
| **Outputs**        | What the tool returns (schema, format)       |
| **Setup**          | Installation and configuration steps         |
| **Example**        | A quick example call                         |
| **Notes**          | Edge cases, limits, auth, or caveats         |

See [`tools/_template/README.md`](tools/_template/README.md) for a ready-to-copy template.

### 4. Include Your Code

Add the tool's source code, dependencies, and any configuration files. Keep it self-contained within your tool folder.

### 5. Open a Pull Request

- Use a clear PR title (e.g., `Add web-search tool`)
- Briefly describe what the tool does and why it's useful
- Link any relevant issues

## Guidelines

- **Keep it focused.** One tool per folder. Don't bundle unrelated utilities together.
- **Document it.** A tool without docs is hard to discover and use. Follow the README format.
- **Make it runnable.** Include setup instructions so someone can get it working quickly.
- **Be honest about limitations.** Note any rate limits, auth requirements, or rough edges.
- **Include a license.** If your tool has a specific license, note it in your tool's README.

## What Makes a Great Contribution

- Clear, concise documentation
- Working example calls
- Tests or mock responses
- Tool schema definitions (JSON Schema, OpenAPI)
- Docker support for easy setup
- Examples for popular agent frameworks

## Code of Conduct

Be respectful, constructive, and inclusive. We're all here to build useful things and help each other out.

## Questions?

Open an issue if you're unsure about anything. We'd rather help you contribute than have you give up.
