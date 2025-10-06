# FalconEYE

**Next-Generation Security Code Analysis Powered by AI**

FalconEYE represents a paradigm shift in static code analysis. Instead of relying on predefined vulnerability patterns, it leverages large language models to reason about your code the same way a security expert would—understanding context, intent, and subtle security implications that traditional tools miss.

## Why FalconEYE?

Traditional security scanners are limited by their pattern databases. They can only find what they've been programmed to look for. FalconEYE is different:

- **No Pattern Matching**: Uses pure AI reasoning to understand your code semantically
- **Context-Aware Analysis**: Retrieval-Augmented Generation provides relevant code context for deeper insights
- **Novel Vulnerability Detection**: Identifies security issues that don't match known patterns
- **Reduced False Positives**: AI validation reduces noise from pattern-based false alarms
- **Smart & Fast**: Incremental analysis means re-scans only process changed files
- **Privacy-First**: Runs entirely locally with Ollama—your code never leaves your machine

## How It Works

FalconEYE follows a sophisticated analysis pipeline:

```
┌─────────────────────────────────────────────────────────────────┐
│                     1. CODE INGESTION                            │
│  Scans repository → Detects languages → Parses AST structure    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                    2. INTELLIGENT INDEXING                       │
│  Chunks code semantically → Generates embeddings → Stores in    │
│  vector database for fast semantic search                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                   3. CONTEXT ASSEMBLY (RAG)                      │
│  For each code segment → Retrieves similar code → Gathers       │
│  relevant context from your entire codebase                     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                    4. AI SECURITY ANALYSIS                       │
│  LLM analyzes code with context → Reasons about vulnerabilities │
│  → Understands data flow → Identifies security implications     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                     5. VALIDATION & REPORTING                    │
│  Optional AI validation pass → Formats findings → Outputs in    │
│  Console/JSON/SARIF format with actionable remediation          │
└─────────────────────────────────────────────────────────────────┘
```

### What Makes This Special?

**Semantic Understanding**: FalconEYE doesn't just scan for known patterns. It reads your code like a security engineer would, understanding business logic, data flows, and architectural patterns to identify real vulnerabilities.

**Smart Re-indexing**: After the initial scan, FalconEYE tracks file changes and only re-analyzes what's changed. This makes subsequent scans dramatically faster while maintaining comprehensive coverage.

**RAG-Enhanced Analysis**: By retrieving similar code patterns from your entire codebase, the AI gets crucial context about how functions are used, what data they handle, and potential security implications across your application.

## Getting Started

### Prerequisites

1. **Python 3.12+** installed
2. **Ollama** running locally ([Install Ollama](https://ollama.ai))

### Installation

```bash
# Pull required AI models
ollama pull qwen3-coder:30b
ollama pull embeddinggemma:300m

# Install FalconEYE
pip install -e .

# Initialize configuration
falconeye config --init
```

### Your First Scan

```bash
# Index your codebase (one-time operation)
falconeye index /path/to/your/project

# Analyze for vulnerabilities
falconeye review /path/to/your/project

# Or do both in one command
falconeye scan /path/to/your/project
```

## Usage Examples

### Single File Analysis

```bash
falconeye review src/auth/login.py
```

Get detailed security analysis of a specific file with context from your entire codebase.

### Directory Analysis

```bash
falconeye review src/api/
```

Analyze all files in a directory with comprehensive coverage.

### Multiple Output Formats

```bash
# Human-readable console output
falconeye review src/ --format console

# Machine-readable JSON
falconeye review src/ --format json --output findings.json

# SARIF for CI/CD integration
falconeye review src/ --format sarif --output results.sarif
```

### Project Management

```bash
# View all indexed projects
falconeye projects list

# Get detailed project statistics
falconeye projects info <project-id>

# Clean up old projects
falconeye projects delete <project-id>
```

## Configuration

FalconEYE uses a hierarchical configuration system. Create `~/.falconeye/config.yaml`:

```yaml
llm:
  model:
    analysis: qwen3-coder:30b      # AI model for security analysis
    embedding: embeddinggemma:300m  # Model for code embeddings
  base_url: http://localhost:11434

analysis:
  top_k_context: 5          # Number of similar code chunks to retrieve
  validate_findings: true    # Enable AI validation pass

logging:
  level: INFO
  log_to_file: true
```

## Supported Languages

FalconEYE analyzes code in multiple languages with language-specific security knowledge:

**Currently Supported:**
Python • JavaScript • TypeScript • Go • Rust • C/C++ • Java • Dart • PHP

**Extensible Plugin System:**
Add new languages by implementing language-specific plugins with tailored security prompts.

## Understanding the Output

### Console Format
```
╭─ SQL Injection Vulnerability ────────────────────────────────╮
│ Severity: HIGH | CWE-89                                       │
│ File: app/database.py:42                                      │
│                                                               │
│ The function executes raw SQL with user input without        │
│ parameterization, allowing SQL injection attacks.            │
│                                                               │
│ Recommendation:                                               │
│ Use parameterized queries or an ORM to safely handle user    │
│ input in database operations.                                │
╰───────────────────────────────────────────────────────────────╯
```

### JSON Format
```json
{
  "findings": [
    {
      "title": "SQL Injection Vulnerability",
      "severity": "high",
      "cwe": "CWE-89",
      "file": "app/database.py",
      "line": 42,
      "description": "...",
      "mitigation": "Use parameterized queries..."
    }
  ]
}
```

### SARIF Format
Industry-standard format compatible with GitHub Security, GitLab, and other DevSecOps platforms.

## CLI Command Reference

| Command | Description |
|---------|-------------|
| `falconeye index <path>` | Index codebase for analysis |
| `falconeye review <path>` | Analyze code for vulnerabilities |
| `falconeye scan <path>` | Index and review in one step |
| `falconeye projects list` | Show all indexed projects |
| `falconeye projects info <id>` | Display project details |
| `falconeye info` | System information |
| `falconeye config --init` | Create default configuration |

Run `falconeye --help` for complete documentation.

## Architecture Overview

FalconEYE is built on **hexagonal architecture** principles, ensuring clean separation between business logic and infrastructure:

```
                    ┌──────────────────┐
                    │   CLI Interface  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Application     │
                    │  Command         │
                    │  Handlers        │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐       ┌──────▼──────┐      ┌────▼────┐
    │ Security│       │  Context    │      │Language │
    │Analyzer │       │  Assembler  │      │Detector │
    └────┬────┘       └──────┬──────┘      └────┬────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  Infrastructure  │
                    ├──────────────────┤
                    │ • Ollama LLM     │
                    │ • Vector Store   │
                    │ • AST Parser     │
                    │ • Logging        │
                    │ • Resilience     │
                    └──────────────────┘
```

**Key Components:**

- **Domain Layer**: Pure business logic for security analysis
- **Application Layer**: Orchestrates use cases and workflows
- **Infrastructure Layer**: Handles external systems (LLM, storage, parsing)
- **Adapters Layer**: User interfaces and output formatting

**Production-Ready Features:**

- Circuit breaker pattern prevents cascade failures
- Exponential backoff retry logic handles transient errors
- Structured JSON logging with correlation IDs
- Thread-safe context management

## Development

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run test suite
pytest

# Run integration tests (requires Ollama)
pytest tests/integration/ -v
```

## Frequently Asked Questions

**Q: Does my code get sent to external services?**
A: No. FalconEYE runs entirely locally using Ollama. Your code never leaves your machine.

**Q: How accurate is AI-based analysis compared to traditional scanners?**
A: FalconEYE complements traditional tools. It excels at finding context-dependent vulnerabilities and novel patterns that signature-based tools miss, while the AI validation reduces false positives.

**Q: How long does analysis take?**
A: Initial indexing depends on codebase size. Subsequent scans with smart re-indexing only process changed files, making them significantly faster.

**Q: Can I use different AI models?**
A: Yes. Configure any Ollama-compatible model in your config file.

**Q: How do I integrate this into CI/CD?**
A: Use SARIF output format which integrates with GitHub Security, GitLab, and most DevSecOps platforms.

## License

MIT License

Copyright (c) 2025 hardw00t

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

**Built for security engineers who demand more than pattern matching.**

Version 2.0.0 | Python 3.12+ | Production Ready
