<div align="center">

```
███████╗ █████╗ ██╗      ██████╗ ██████╗ ███╗   ██╗███████╗██╗   ██╗███████╗
██╔════╝██╔══██╗██║     ██╔════╝██╔═══██╗████╗  ██║██╔════╝╚██╗ ██╔╝██╔════╝
█████╗  ███████║██║     ██║     ██║   ██║██╔██╗ ██║█████╗   ╚████╔╝ █████╗  
██╔══╝  ██╔══██║██║     ██║     ██║   ██║██║╚██╗██║██╔══╝    ╚██╔╝  ██╔══╝  
██║     ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║███████╗   ██║   ███████╗
╚═╝     ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚══════╝
```

### **AI-Powered Security Code Review That Actually Understands Your Code**

*Next-generation static analysis using local LLMs and semantic reasoning*

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

[Features](#-key-features) •
[Quick Start](#-quick-start) •
[Demo](#-demo) •
[Documentation](#-documentation) •
[Contributing](#-contributing)

</div>

---

## 🎯 What is FalconEYE?

FalconEYE is a **revolutionary security code analyzer** that goes beyond traditional pattern matching. Instead of relying on predefined vulnerability signatures, it uses **Large Language Models** to reason about your code the same way a security expert would—understanding context, data flow, and business logic.

### 💡 The Problem

Traditional security scanners are limited:
- ❌ Only find known patterns
- ❌ Miss context-dependent vulnerabilities  
- ❌ Generate excessive false positives
- ❌ Can't understand business logic
- ❌ Require constant signature updates

### ✨ The FalconEYE Solution

- ✅ **Semantic Understanding**: AI reads code like a human security engineer
- ✅ **Context-Aware Analysis**: RAG provides full codebase context
- ✅ **Novel Vulnerability Detection**: Finds issues that don't match known patterns
- ✅ **Reduced False Positives**: AI validation filters out noise
- ✅ **Privacy-First**: Runs 100% locally—your code never leaves your machine
- ✅ **Smart & Fast**: Incremental scanning only processes changed files

---

## 🚀 Quick Start

### Prerequisites

```bash
# 1. Install Python 3.12+
python --version  # Should be 3.12 or higher

# 2. Install and start Ollama
# Visit: https://ollama.ai
ollama serve

# 3. Pull required AI models
ollama pull qwen3-coder:30b      # Analysis model
ollama pull embeddinggemma:300m  # Embedding model
```

### Installation

```bash
# Clone the repository
git clone https://github.com/hardw00t/FalconEYE.git
cd FalconEYE

# Install FalconEYE
pip install -e .

# Initialize configuration
falconeye config --init
```

### Your First Scan

```bash
# Scan your project (index + analyze in one command)
falconeye scan /path/to/your/project

# View the beautiful HTML report
open falconeye_reports/falconeye_project_*.html
```

That's it! 🎉 FalconEYE will analyze your code and generate:
- 📊 **Interactive HTML report** with executive dashboard
- 📄 **JSON report** for programmatic access
- 🎨 **Color-coded findings** by severity

---

## 🎨 Demo

### Terminal Output
```bash
$ falconeye scan ./myapp

███████╗ █████╗ ██╗      ██████╗ ██████╗ ███╗   ██╗███████╗██╗   ██╗███████╗
██╔════╝██╔══██╗██║     ██╔════╝██╔═══██╗████╗  ██║██╔════╝╚██╗ ██╔╝██╔════╝
█████╗  ███████║██║     ██║     ██║   ██║██╔██╗ ██║█████╗   ╚████╔╝ █████╗  
██╔══╝  ██╔══██║██║     ██║     ██║   ██║██║╚██╗██║██╔══╝    ╚██╔╝  ██╔══╝  
██║     ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║███████╗   ██║   ███████╗
╚═╝     ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚══════╝

                        Security Code Review
                     v2.0 - AI-Powered Analysis
                     by hardw00t & h4ckologic

Indexing codebase...
Indexed 127 files in 8.3s

Analyzing for vulnerabilities...
Found 12 potential issues

Results saved to: falconeye_reports/falconeye_myapp_20251113_130425.html
```

## ✨ Key Features

### AI-Powered Analysis
- **Semantic Code Understanding**: Goes beyond pattern matching to understand intent and data flow
- **RAG-Enhanced Context**: Retrieves similar code patterns from your entire codebase
- **Confidence Scoring**: AI rates its confidence in each finding
- **CWE Mapping**: Maps vulnerabilities to Common Weakness Enumeration

### Enhanced CLI Experience
- **ASCII Art Banner**: Stylish cyan-themed banner on every command
- **Rich Console Output**: Color-coded terminal output with progress indicators
- **Smart Error Messages**: Clear, actionable error messages with solutions
- **Graceful Degradation**: Continues analysis even when individual files fail

### Robust Processing
- **Advanced JSON Parsing**: Multi-layer escape sequence fixing for AI responses
- **Automatic Line Numbers**: Populates line numbers from source files
- **Context Expansion**: Automatically expands code snippets with surrounding context
- **Debug File Generation**: Saves problematic responses for troubleshooting

### Multiple Output Formats
- **Console**: Rich, color-coded terminal output
- **JSON**: Machine-readable format for CI/CD integration
- **HTML**: Interactive reports with executive summaries
- **SARIF**: Industry-standard format for security platforms

### Performance
- **Incremental Scanning**: Only re-analyzes changed files after initial scan
- **Parallel Processing**: Batch processing for faster analysis
- **Smart Caching**: Reuses embeddings and context when possible
- **Optimized Chunking**: Intelligent code segmentation for better context

---

## 📚 Documentation

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CODE INGESTION                                                │
│    Scan repository → Detect languages → Parse AST structure     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ 2. INTELLIGENT INDEXING                                          │
│    Chunk code semantically → Generate embeddings → Store in     │
│    vector database for fast semantic search                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ 3. CONTEXT ASSEMBLY (RAG)                                        │
│    For each code segment → Retrieve similar code → Gather       │
│    relevant context from your entire codebase                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ 4. AI SECURITY ANALYSIS                                          │
│    LLM analyzes code with context → Reasons about               │
│    vulnerabilities → Understands data flow                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ 5. VALIDATION & REPORTING                                        │
│    Optional AI validation pass → Format findings → Output in    │
│    Console/JSON/HTML/SARIF with actionable remediation          │
└─────────────────────────────────────────────────────────────────┘
```

### Usage Examples

#### Basic Scanning
```bash
# Scan entire project
falconeye scan /path/to/project

# Scan specific directory
falconeye scan ./src

# Scan single file
falconeye review ./src/auth/login.py
```

#### Advanced Options
```bash
# Filter by severity
falconeye review ./src --severity high

# Enable AI validation for fewer false positives
falconeye review ./src --validate

# Custom output format
falconeye review ./src --format html --output report.html

# Exclude paths
falconeye index ./src --exclude "*/tests/*" --exclude "*.min.js"

# Force full re-index
falconeye index ./src --force-reindex
```

#### Project Management
```bash
# List all indexed projects
falconeye projects list

# View project details
falconeye projects info <project-id>

# Delete project data
falconeye projects delete <project-id>

# Clean up orphaned files
falconeye projects cleanup <project-id>
```

#### Configuration
```bash
# Initialize default config
falconeye config --init

# Show current configuration
falconeye config --show

# System information
falconeye info
```

### Configuration

Create `~/.falconeye/config.yaml` to customize settings:

```yaml
llm:
  provider: ollama
  model:
    analysis: qwen3-coder:30b
    embedding: embeddinggemma:300m
  base_url: http://localhost:11434
  timeout: 600

analysis:
  top_k_context: 5          # Number of similar code chunks to retrieve
  validate_findings: true    # Enable AI validation pass
  batch_size: 10            # Files to process in parallel

logging:
  level: INFO
  file: ./falconeye.log
  console: true
```

See [config.yaml](config.yaml) for all available options.

---

## 🌍 Supported Languages

<div align="center">

| Language | Status | Language | Status |
|----------|--------|----------|--------|
| Python | ✅ Full Support | JavaScript | ✅ Full Support |
| TypeScript | ✅ Full Support | Go | ✅ Full Support |
| Rust | ✅ Full Support | C | ✅ Full Support |
| C++ | ✅ Full Support | Java | ✅ Full Support |
| Dart | ✅ Full Support | PHP | ✅ Full Support |
| Ruby | ✅ Full Support | | |

</div>

Want to add a language? Check out our [Contributing Guide](#-contributing)!

---

## 🎨 Output Formats

### Console Output
```
╭─ SQL Injection Vulnerability ────────────────────────────────╮
│ Severity: HIGH | CWE-89 | Confidence: HIGH                   │
│ File: app/database.py:42-45                                  │
│                                                               │
│ The function executes raw SQL with user input without        │
│ parameterization, allowing SQL injection attacks.            │
│                                                               │
│ Recommendation:                                               │
│ Use parameterized queries or an ORM to safely handle user    │
│ input in database operations.                                │
╰───────────────────────────────────────────────────────────────╯
```

### JSON Output
```json
{
  "scan_metadata": {
    "project": "/path/to/project",
    "language": "python",
    "started_at": "2025-11-13T12:30:45Z",
    "duration": "45.3s",
    "files_analyzed": 127
  },
  "summary": {
    "total_findings": 12,
    "by_severity": {
      "critical": 2,
      "high": 4,
      "medium": 5,
      "low": 1
    }
  },
  "findings": [
    {
      "id": "uuid-here",
      "issue": "SQL Injection Vulnerability",
      "severity": "high",
      "confidence": {"value": "high", "level": "high"},
      "location": {
        "file_path": "app/database.py",
        "line_start": 42,
        "line_end": 45
      },
      "code_snippet": "def get_user(username):\n    query = f\"SELECT * FROM users WHERE username = '{username}'\"\n    return db.execute(query)",
      "reasoning": "Direct string interpolation of user input into SQL query...",
      "mitigation": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE username = ?', (username,))",
      "cwe_id": "CWE-89",
      "tags": ["sql-injection", "database", "user-input"]
    }
  ]
}
```

### HTML Report
- **Executive Dashboard** with statistics and charts
- **Interactive Filtering** by severity
- **Color-Coded Findings** with detailed information
- **Code Snippets** with syntax highlighting
- **Responsive Design** for all devices
- **Print-Friendly** for PDF export

### SARIF Output
Industry-standard format compatible with:
- GitHub Security
- GitLab Security Dashboard
- Azure DevOps
- SonarQube
- And more...

---

## 🔒 Security & Privacy

### Privacy-First Design
- ✅ **100% Local Processing**: All analysis happens on your machine
- ✅ **No External API Calls**: Uses local Ollama instance
- ✅ **No Data Collection**: Your code never leaves your environment
- ✅ **No Telemetry**: No usage tracking or analytics

### Security Best Practices
- 🔐 Secure configuration management
- 🔐 Input validation and sanitization
- 🔐 Safe file handling
- 🔐 Dependency security scanning

---

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### Areas for Contribution
- 🌐 **Language Support**: Add support for new programming languages
- 📊 **Output Formats**: Implement new report formats (PDF, CSV, etc.)
- 🎨 **HTML Templates**: Create custom report templates
- 🔌 **Integrations**: Build integrations with security platforms
- ⚡ **Performance**: Optimize analysis speed and memory usage
- 📚 **Documentation**: Improve guides and examples

### Pull Request Process
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Update documentation
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to your branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

---

## 📖 Additional Resources

### Documentation
- [Architecture Guide](docs/ARCHITECTURE_SUMMARY.md)
- [Smart Re-indexing Guide](docs/SMART_REINDEXING_GUIDE.md)
- [Implementation Status](docs/IMPLEMENTATION_STATUS.md)
- [Migration Guide](docs/MIGRATION_GUIDE.md)

### Community
- 💬 [Discussions](https://github.com/hardw00t/FalconEYE/discussions) - Ask questions and share ideas
- 🐛 [Issue Tracker](https://github.com/hardw00t/FalconEYE/issues) - Report bugs and request features
- 📧 Contact: [Create an issue](https://github.com/hardw00t/FalconEYE/issues/new)

---

## ❓ FAQ

<details>
<summary><b>Does my code get sent to external services?</b></summary>

No. FalconEYE runs entirely locally using Ollama. Your code never leaves your machine.
</details>

<details>
<summary><b>How accurate is AI-based analysis compared to traditional scanners?</b></summary>

FalconEYE complements traditional tools. It excels at finding context-dependent vulnerabilities and novel patterns that signature-based tools miss, while AI validation reduces false positives.
</details>

<details>
<summary><b>How long does analysis take?</b></summary>

Initial indexing depends on codebase size (typically 1-5 minutes for medium projects). Subsequent scans with smart re-indexing only process changed files, making them significantly faster (seconds to minutes).
</details>

<details>
<summary><b>Can I use different AI models?</b></summary>

Yes! Configure any Ollama-compatible model in your config file. We recommend `qwen3-coder:30b` for analysis and `embeddinggemma:300m` for embeddings.
</details>

<details>
<summary><b>How do I integrate this into CI/CD?</b></summary>

Use SARIF output format which integrates with GitHub Security, GitLab, and most DevSecOps platforms:
```bash
falconeye scan ./src --format sarif --output results.sarif
```
</details>
---

## 📊 Project Stats

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/hardw00t/FalconEYE?style=social)
![GitHub forks](https://img.shields.io/github/forks/hardw00t/FalconEYE?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/hardw00t/FalconEYE?style=social)

</div>

---

## 📝 License

MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 hardw00t & h4ckologic

---

## 🙏 Acknowledgments

- Built with [Ollama](https://ollama.ai) for local LLM inference
- Powered by [ChromaDB](https://www.trychroma.com/) for vector storage
- Uses [Tree-sitter](https://tree-sitter.github.io/) for AST parsing
- CLI built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/)

---

<div align="center">

**Built for security engineers who demand more than pattern matching.**

Version 2.0.0 | Python 3.12+ | Production Ready

Made with ❤️ by [hardw00t](https://github.com/hardw00t) & [h4ckologic](https://github.com/h4ckologic)

</div>
