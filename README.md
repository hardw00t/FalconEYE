# FalconEYE v2.0

**AI-Powered Security Code Review - Pure AI Analysis with ZERO Pattern Matching**

FalconEYE v2.0 is a complete reimplementation of the security code review tool, built from the ground up with hexagonal architecture and powered entirely by AI reasoning through Ollama.

## Key Features

- **Pure AI Analysis**: ZERO pattern matching - all vulnerability detection through LLM reasoning
- **RAG-Enhanced**: Retrieval-Augmented Generation provides context for better analysis
- **⚡ Smart Re-indexing**: 90%+ faster re-scans - only processes changed files
- **🎯 Project Isolation**: Automatic project tracking and management
- **Multi-Language**: Python, JavaScript, TypeScript (extensible for more languages)
- **Professional CLI**: Modern Typer-based interface with rich console output
- **Multiple Outputs**: Console (colored), JSON, SARIF 2.1.0
- **Flexible Configuration**: YAML files, environment variables, hierarchical loading
- **Clean Architecture**: Hexagonal architecture with DDD principles
- **Fast Embeddings**: Uses Ollama for local embedding generation
- **Extensible**: Plugin system for language-specific analysis

## Quick Start

### Prerequisites

- Python 3.12+
- Ollama running locally
- Required models: `ollama pull qwen3-coder:32b && ollama pull embeddinggemma:300m`

### Installation

```bash
pip install -e .
```

### Usage

```bash
# Create default configuration
falconeye config --init

# Index a codebase (first time)
falconeye index /path/to/code

# Re-index later (smart re-indexing - only changed files processed!)
falconeye index /path/to/code  # 90%+ faster

# Review code
falconeye review /path/to/file.py

# Scan (index + review)
falconeye scan /path/to/code

# Show system info
falconeye info

# Manage projects
falconeye projects list
falconeye projects info <project-id>
```

## CLI Commands

### Core Commands

- `falconeye index <path>` - Index codebase (smart re-indexing enabled)
  - `--project-id <id>` - Explicit project identifier
  - `--force-reindex` - Skip smart re-indexing (process all files)
- `falconeye review <path>` - Review code for vulnerabilities
- `falconeye scan <path>` - Index and review in one command
- `falconeye info` - Show system information
- `falconeye config` - Manage configuration

### Project Management

- `falconeye projects list` - List all indexed projects
- `falconeye projects info <id>` - Show detailed project information
- `falconeye projects delete <id>` - Delete a project
- `falconeye projects cleanup <id>` - Remove deleted files from index

Run `falconeye --help` or `falconeye <command> --help` for detailed options.

## Output Formats

- **Console**: Rich colored output with severity icons
- **JSON**: Machine-readable structured output
- **SARIF**: Industry-standard format for CI/CD integration

## Documentation

### User Guides

- **[Smart Re-indexing Guide](docs/SMART_REINDEXING_GUIDE.md)** - Performance optimization features
- **[Migration Guide](docs/MIGRATION_GUIDE.md)** - Upgrading from v1.x to v2.0

### Development Progress

- [Phase 1 Progress](PHASE1_PROGRESS.md) - Domain layer implementation
- [Phase 2 Progress](PHASE2_PROGRESS.md) - Infrastructure and application layers
- [Phase 3 Progress](PHASE3_PROGRESS.md) - Configuration, plugins, CLI
- [Phase 3 Design](PHASE3_DESIGN.md) - Architecture design details
- [Phase 4 Complete](PHASE_4_COMPLETE.md) - Smart re-indexing implementation
- [Phase 5 Complete](PHASE_5_COMPLETE.md) - Project management CLI
- [Phase 6 Complete](PHASE_6_COMPLETE.md) - Integration testing

## Architecture

FalconEYE v2.0 follows hexagonal architecture with clean separation:

- **Domain**: Business logic (pure, no dependencies)
- **Application**: Use cases and commands
- **Infrastructure**: External adapters (LLM, vector store, AST)
- **Adapters**: User interfaces (CLI, formatters)

## How It Works

1. **Pure AI Analysis**: No pattern matching - LLM reasons about code
2. **RAG Enhancement**: Retrieves similar code for context
3. **Smart Re-indexing**: Automatic change detection - only processes modified files
4. **Project Isolation**: Separate tracking per codebase with unique identifiers
5. **Language Plugins**: Tailored prompts per language
6. **Optional Validation**: Second-pass validation to reduce false positives

### Performance

- **First-time indexing**: 10-15 seconds (100 files), 1-2 minutes (1,000 files)
- **Smart re-indexing (no changes)**: 2-6 seconds (any size project)
- **Smart re-indexing (few changes)**: 10-30 seconds (proportional to changes)

**Example**: 10,000 file project with 15 changes
- Traditional: ~3-5 minutes
- Smart re-indexing: ~20 seconds (**91% faster**)

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run integration tests
pytest tests/integration/ -v
```

## Contributing

Contributions welcome! Areas to contribute:

- Additional language plugins (Go, Rust, Java, C++, Ruby)
- Performance optimizations
- Additional output formats
- IDE integrations

## License

[Add your license]

---

**Built with**: Ollama, ChromaDB, Typer, Rich, Tree-sitter, Pydantic
