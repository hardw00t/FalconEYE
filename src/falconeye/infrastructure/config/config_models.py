"""Configuration data models using Pydantic."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class LLMModelConfig(BaseModel):
    """LLM model configuration."""
    analysis: str = Field(
        default="qwen3-coder:30b",
        description="Model for security analysis"
    )
    embedding: str = Field(
        default="embeddinggemma:300m",
        description="Model for generating embeddings"
    )


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = Field(
        default="ollama",
        description="LLM provider (ollama, openai)"
    )
    model: LLMModelConfig = Field(default_factory=LLMModelConfig)
    base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for LLM API"
    )
    timeout: int = Field(
        default=120,
        ge=10,
        le=600,
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retries for failed requests"
    )


class VectorStoreConfig(BaseModel):
    """Vector store configuration."""
    provider: str = Field(
        default="chroma",
        description="Vector store provider (chroma, postgres)"
    )
    persist_directory: str = Field(
        default="./falconeye_data/vectorstore",
        description="Directory for vector store persistence"
    )
    collection_prefix: str = Field(
        default="falconeye",
        description="Prefix for collection names"
    )


class MetadataConfig(BaseModel):
    """Metadata repository configuration."""
    provider: str = Field(
        default="chroma",
        description="Metadata provider (chroma, postgres)"
    )
    persist_directory: str = Field(
        default="./falconeye_data/metadata",
        description="Directory for metadata persistence"
    )
    collection_name: str = Field(
        default="metadata",
        description="Collection name for metadata"
    )


class IndexRegistryConfig(BaseModel):
    """Index registry configuration for project tracking."""
    persist_directory: str = Field(
        default="./falconeye_data/registry",
        description="Directory for registry persistence"
    )
    collection_name: str = Field(
        default="index_registry",
        description="Collection name for index registry"
    )


class ChunkingConfig(BaseModel):
    """Code chunking configuration."""
    default_size: int = Field(
        default=50,
        ge=10,
        le=500,
        description="Default lines per chunk"
    )
    default_overlap: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Default lines of overlap between chunks"
    )
    max_chunk_size: int = Field(
        default=200,
        ge=50,
        le=1000,
        description="Maximum lines per chunk"
    )

    @field_validator('default_overlap')
    @classmethod
    def validate_overlap(cls, v, info):
        """Ensure overlap is less than chunk size."""
        if 'default_size' in info.data and v >= info.data['default_size']:
            raise ValueError("overlap must be less than chunk_size")
        return v


class AnalysisConfig(BaseModel):
    """Security analysis configuration."""
    top_k_context: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of similar chunks for RAG context"
    )
    validate_findings: bool = Field(
        default=False,
        description="Enable AI-based validation to reduce false positives"
    )
    batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of files to process in parallel"
    )


class LanguagesConfig(BaseModel):
    """Language support configuration."""
    enabled: List[str] = Field(
        default_factory=lambda: [
            "python",
            "javascript",
            "typescript",
            "go",
            "rust",
            "c",
            "cpp",
            "java",
            "dart",
            "php",
        ],
        description="List of enabled languages"
    )


class FileDiscoveryConfig(BaseModel):
    """File discovery configuration."""
    default_exclusions: List[str] = Field(
        default_factory=lambda: [
            "*/node_modules/*",
            "*/venv/*",
            "*/virtualenv/*",
            "*/.git/*",
            "*/dist/*",
            "*/build/*",
            "*/__pycache__/*",
            "*/target/*",
            "*.min.js",
            "*.pyc",
        ],
        description="Default file/directory exclusion patterns"
    )


class OutputConfig(BaseModel):
    """Output configuration."""
    default_format: str = Field(
        default="json",
        description="Default output format (console, json, sarif)"
    )
    color: bool = Field(
        default=True,
        description="Enable colored console output"
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose output"
    )
    save_to_file: bool = Field(
        default=False,
        description="Save output to file"
    )
    output_directory: str = Field(
        default="./falconeye_reports",
        description="Directory for saving reports"
    )

    @field_validator('default_format')
    @classmethod
    def validate_format(cls, v):
        """Ensure format is valid."""
        valid_formats = ["console", "json", "sarif"]
        if v not in valid_formats:
            raise ValueError(f"format must be one of {valid_formats}")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    file: str = Field(
        default="./falconeye.log",
        description="Log file path"
    )
    console: bool = Field(
        default=True,
        description="Enable console logging"
    )

    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        """Ensure log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"level must be one of {valid_levels}")
        return v


class FalconEyeConfig(BaseModel):
    """Complete FalconEYE configuration."""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    index_registry: IndexRegistryConfig = Field(default_factory=IndexRegistryConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    languages: LanguagesConfig = Field(default_factory=LanguagesConfig)
    file_discovery: FileDiscoveryConfig = Field(default_factory=FileDiscoveryConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Forbid extra fields
        validate_assignment = True  # Validate on assignment

    def to_yaml(self) -> str:
        """Convert configuration to YAML string."""
        import yaml
        return yaml.dump(self.model_dump(), default_flow_style=False, sort_keys=False)