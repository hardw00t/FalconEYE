"""Index codebase command and handler."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import asyncio

from ...domain.models.codebase import Codebase, CodeFile
from ...domain.models.code_chunk import CodeChunk, ChunkMetadata
from ...domain.models.document import Document, DocumentChunk, DocumentMetadata
from ...domain.services.llm_service import LLMService
from ...domain.services.language_detector import LanguageDetector
from ...domain.services.project_identifier import ProjectIdentifier
from ...domain.services.checksum_service import ChecksumService
from ...domain.repositories.vector_store_repository import VectorStoreRepository
from ...domain.repositories.metadata_repository import MetadataRepository
from ...domain.repositories.index_registry import IndexRegistryRepository
from ...domain.value_objects.project_metadata import ProjectMetadata, FileMetadata, FileStatus
from ...infrastructure.ast.ast_analyzer import EnhancedASTAnalyzer


@dataclass
class IndexCodebaseCommand:
    """
    Command to index a codebase.

    This builds the vector index used for RAG,
    NOT for pattern-based detection.

    New in v2.0: Smart re-indexing with project isolation
    """
    codebase_path: Path
    language: Optional[str] = None
    excluded_patterns: Optional[List[str]] = None
    chunk_size: int = 40  # lines per chunk
    chunk_overlap: int = 15  # lines overlap
    include_documents: bool = True  # Whether to index documentation files
    doc_chunk_size: int = 1000  # characters per document chunk

    # Smart re-indexing fields
    project_id: Optional[str] = None  # Explicit project ID override (for monorepos)
    force_reindex: bool = False  # Force re-index all files regardless of changes


class IndexCodebaseHandler:
    """
    Handler for index codebase command.

    Orchestrates:
    1. Project identification (git/non-git)
    2. Smart re-indexing (detect changed/new/deleted files)
    3. Language detection
    4. File discovery (code + documents)
    5. AST analysis (code only)
    6. Chunking (code + documents)
    7. Embedding generation (code + documents)
    8. Vector storage (project-scoped collections)
    9. Registry updates (project & file metadata)
    """

    def __init__(
        self,
        vector_store: VectorStoreRepository,
        metadata_repo: MetadataRepository,
        llm_service: LLMService,
        language_detector: LanguageDetector,
        ast_analyzer: EnhancedASTAnalyzer,
        project_identifier: ProjectIdentifier,
        checksum_service: ChecksumService,
        index_registry: IndexRegistryRepository,
    ):
        """
        Initialize handler.

        Args:
            vector_store: Vector storage for embeddings
            metadata_repo: Metadata storage for AST data
            llm_service: LLM for embedding generation
            language_detector: Language detection service
            ast_analyzer: AST analyzer for metadata extraction
            project_identifier: Project identification service
            checksum_service: File change detection service
            index_registry: Registry for project/file metadata
        """
        self.vector_store = vector_store
        self.metadata_repo = metadata_repo
        self.llm_service = llm_service
        self.language_detector = language_detector
        self.ast_analyzer = ast_analyzer
        self.project_identifier = project_identifier
        self.checksum_service = checksum_service
        self.index_registry = index_registry

    async def handle(self, command: IndexCodebaseCommand) -> Codebase:
        """
        Execute index codebase command with smart re-indexing.

        Args:
            command: Index command

        Returns:
            Indexed codebase

        Flow:
        1. Identify project (auto-detect or use explicit project_id)
        2. Check registry for previous indexing
        3. Detect changed/new/deleted files
        4. Process only changed/new files (or all if force_reindex=True)
        5. Update registry with new metadata
        """
        print(f"Indexing codebase: {command.codebase_path}")

        # Step 1: Identify project
        project_id, project_name, project_type, git_remote_url = \
            self.project_identifier.identify_project(
                command.codebase_path,
                explicit_id=command.project_id
            )

        print(f"Project ID: {project_id}")
        print(f"Project type: {project_type.value}")

        # Step 2: Detect language
        if command.language:
            language = command.language
        else:
            language = self.language_detector.detect_language(command.codebase_path)

        print(f"Detected language: {language}")

        # Step 3: Check registry for previous indexing
        existing_project = self.index_registry.get_project(project_id)
        is_first_time = existing_project is None

        if is_first_time:
            print("First-time indexing for this project")
        else:
            last_indexed = existing_project.indexed_at if hasattr(existing_project, 'indexed_at') else "unknown"
            print(f"Re-indexing (last indexed: {last_indexed})")

        # Step 4: Discover current files
        files = self._discover_files(command.codebase_path, language, command.excluded_patterns or [])
        print(f"Found {len(files)} code files")

        # Step 5: Determine which files to process
        if command.force_reindex or is_first_time:
            files_to_process = files
            skipped_count = 0
            print(f"Processing all {len(files)} files (force={command.force_reindex}, first_time={is_first_time})")
        else:
            # Smart re-indexing: only process changed/new files
            files_to_process, skipped_count = await self._filter_changed_files(
                project_id, files, command.codebase_path
            )
            print(f"Smart re-index: {len(files_to_process)} changed/new, {skipped_count} unchanged")

        # Step 6: Handle deleted files
        if not is_first_time and not command.force_reindex:
            await self._handle_deleted_files(project_id, files, command.codebase_path)

        # Step 7: Create codebase entity
        codebase = Codebase.create(
            root_path=command.codebase_path,
            language=language,
            excluded_patterns=command.excluded_patterns or [],
        )

        # Step 8: Process code files
        processed_files = []
        for file_path in files_to_process:
            file_meta = await self._process_file(
                file_path, language, command, codebase, project_id
            )
            if file_meta:
                processed_files.append(file_meta)

        # Step 9: Process documents if enabled
        doc_count = 0
        if command.include_documents:
            doc_files = self._discover_documents(command.codebase_path, command.excluded_patterns or [])
            print(f"Found {len(doc_files)} documentation files")

            for doc_path in doc_files:
                await self._process_document(doc_path, command)
                doc_count += 1

        # Step 10: Update project metadata in registry
        project_metadata = ProjectMetadata(
            project_id=project_id,
            project_name=project_name,
            project_root=command.codebase_path,
            project_type=project_type,
            git_remote_url=git_remote_url if project_type.value == "git" else None,
            last_indexed_commit=self._get_current_commit(command.codebase_path) if project_type.value == "git" else None,
            total_files=len(files),
            total_chunks=sum(f.chunk_count for f in processed_files),
            languages=[language],
        )
        self.index_registry.save_project(project_metadata)

        print(f"\nIndexing complete:")
        print(f"  Project: {project_name} ({project_id})")
        print(f"  Files processed: {len(files_to_process)}")
        print(f"  Files skipped: {skipped_count}")
        print(f"  Documents: {doc_count}")
        print(f"  Total files: {codebase.total_files}, Total lines: {codebase.total_lines}")

        return codebase

    async def _process_file(
        self,
        file_path: Path,
        language: str,
        command: IndexCodebaseCommand,
        codebase: Codebase,
        project_id: str,
    ) -> Optional[FileMetadata]:
        """
        Process a single file and return file metadata.

        Args:
            file_path: Absolute path to file
            language: Programming language
            command: Index command
            codebase: Codebase entity
            project_id: Project identifier

        Returns:
            FileMetadata if successful, None otherwise
        """
        try:
            # Read file
            content = file_path.read_text(encoding="utf-8")

            # Create code file
            relative_path = file_path.relative_to(command.codebase_path)
            code_file = CodeFile.create(
                path=file_path,
                relative_path=str(relative_path),
                content=content,
                language=language,
            )
            codebase.add_file(code_file)

            # Extract AST metadata
            metadata = self.ast_analyzer.analyze_file(
                file_path=str(relative_path),
                content=content,
            )

            # Store metadata
            await self.metadata_repo.store_metadata(metadata)

            # Chunk the file
            chunks = self._chunk_content(
                content=content,
                file_path=str(relative_path),
                language=language,
                chunk_size=command.chunk_size,
                overlap=command.chunk_overlap,
            )

            # Generate embeddings in batch
            texts = [chunk.content for chunk in chunks]
            embeddings = await self.llm_service.generate_embeddings_batch(texts)

            # Add embeddings to chunks
            chunks_with_embeddings = [
                chunk.with_embedding(embedding)
                for chunk, embedding in zip(chunks, embeddings)
            ]

            # Store chunks (project-scoped collection)
            await self.vector_store.store_chunks(chunks_with_embeddings, collection="code")

            # Get embedding IDs (if vector store supports it)
            embedding_ids = [str(chunk.id) if hasattr(chunk, 'id') else f"chunk_{i}"
                           for i, chunk in enumerate(chunks_with_embeddings)]

            # Create file metadata snapshot
            file_metadata = self.checksum_service.get_file_metadata_snapshot(
                file_path=file_path,
                relative_path=relative_path,
                project_id=project_id,
                language=language,
                git_commit_hash=self._get_current_commit(command.codebase_path),
            )

            # Update with chunk info
            file_metadata = FileMetadata(
                project_id=file_metadata.project_id,
                file_path=file_metadata.file_path,
                relative_path=file_metadata.relative_path,
                language=file_metadata.language,
                file_checksum=file_metadata.file_checksum,
                file_size=file_metadata.file_size,
                file_mtime=file_metadata.file_mtime,
                git_commit_hash=file_metadata.git_commit_hash,
                git_file_hash=file_metadata.git_file_hash,
                indexed_at=file_metadata.indexed_at,
                chunk_count=len(chunks),
                embedding_ids=embedding_ids,
                status=FileStatus.ACTIVE,
            )

            # Save to registry
            self.index_registry.save_file(file_metadata)

            print(f"  Processed: {relative_path} ({len(chunks)} chunks)")

            return file_metadata

        except Exception as e:
            print(f"  Error processing {file_path}: {e}")
            return None

    async def _filter_changed_files(
        self,
        project_id: str,
        current_files: List[Path],
        project_root: Path,
    ) -> tuple[List[Path], int]:
        """
        Filter files to only process changed/new ones.

        Args:
            project_id: Project identifier
            current_files: List of current files in project
            project_root: Project root path

        Returns:
            Tuple of (files_to_process, skipped_count)
        """
        # Get cached file metadata from registry
        cached_metadata = self.index_registry.get_files_metadata_dict(project_id)

        # Use checksum service to filter changed files
        changed_files, unchanged_files = self.checksum_service.filter_changed_files_efficient(
            current_files,
            cached_metadata,
            use_checksum=False,  # Use quick check (mtime + size)
        )

        # Identify new files
        new_files = self.checksum_service.identify_new_files(
            set(current_files),
            set(cached_metadata.keys())
        )

        # Combine changed and new files
        files_to_process = list(set(changed_files) | new_files)
        skipped_count = len(unchanged_files)

        return files_to_process, skipped_count

    async def _handle_deleted_files(
        self,
        project_id: str,
        current_files: List[Path],
        project_root: Path,
    ):
        """
        Handle deleted files by marking them in registry.

        Args:
            project_id: Project identifier
            current_files: List of current files in project
            project_root: Project root path
        """
        # Get cached file metadata
        cached_metadata = self.index_registry.get_files_metadata_dict(project_id)

        # Identify deleted files
        deleted_files = self.checksum_service.identify_deleted_files(
            set(current_files),
            set(cached_metadata.keys())
        )

        if deleted_files:
            print(f"\nDetected {len(deleted_files)} deleted files:")
            for deleted_file in deleted_files:
                relative_path = deleted_file.relative_to(project_root) if deleted_file.is_absolute() else deleted_file
                print(f"  - {relative_path}")

                # Mark as deleted in registry
                self.index_registry.mark_file_deleted(project_id, deleted_file)

            # TODO: In Phase 6, add user prompt to delete embeddings from vector store
            print("  (Embeddings marked for cleanup - use 'falconeye projects cleanup' to remove)")

    def _get_current_commit(self, project_root: Path) -> Optional[str]:
        """
        Get current git commit hash if project is a git repository.

        Args:
            project_root: Project root path

        Returns:
            Commit hash or None
        """
        try:
            return self.project_identifier.get_current_git_commit(project_root)
        except Exception:
            return None

    def _discover_files(
        self,
        root_path: Path,
        language: str,
        excluded_patterns: List[str],
    ) -> List[Path]:
        """
        Discover source files.

        Args:
            root_path: Root directory
            language: Primary language
            excluded_patterns: Patterns to exclude

        Returns:
            List of file paths
        """
        # Get extensions for language
        extensions = self.language_detector.LANGUAGE_EXTENSIONS.get(language, [])

        files = []
        for ext in extensions:
            # Find all files with this extension
            found = list(root_path.rglob(f"*{ext}"))
            files.extend(found)

        # Filter excluded patterns
        filtered_files = []
        for file_path in files:
            should_exclude = False
            relative_path = str(file_path.relative_to(root_path))

            for pattern in excluded_patterns:
                # Simple pattern matching (can be enhanced)
                pattern_clean = pattern.replace("**", "").replace("*", "")
                if pattern_clean in relative_path or pattern_clean in str(file_path):
                    should_exclude = True
                    break

            if not should_exclude:
                filtered_files.append(file_path)

        return filtered_files

    def _chunk_content(
        self,
        content: str,
        file_path: str,
        language: str,
        chunk_size: int,
        overlap: int,
    ) -> List[CodeChunk]:
        """
        Chunk file content.

        Chunks at line boundaries, NOT arbitrary character counts.

        Args:
            content: File content
            file_path: File path
            language: Language
            chunk_size: Lines per chunk
            overlap: Overlap lines

        Returns:
            List of code chunks
        """
        lines = content.splitlines(keepends=True)
        chunks = []

        start = 0
        chunk_index = 0

        while start < len(lines):
            end = min(start + chunk_size, len(lines))

            # Get chunk content
            chunk_lines = lines[start:end]
            chunk_content = "".join(chunk_lines)

            # Create metadata
            metadata = ChunkMetadata(
                file_path=file_path,
                language=language,
                start_line=start + 1,
                end_line=end,
                chunk_index=chunk_index,
                total_chunks=0,  # Will be updated
            )

            # Create chunk
            chunk = CodeChunk.create(
                content=chunk_content,
                metadata=metadata,
                token_count=self.llm_service.count_tokens(chunk_content),
            )

            chunks.append(chunk)
            chunk_index += 1

            # Move to next chunk with overlap
            start += (chunk_size - overlap)

        # Update total chunks
        chunks = [
            CodeChunk.create(
                content=chunk.content,
                metadata=ChunkMetadata(
                    file_path=chunk.metadata.file_path,
                    language=chunk.metadata.language,
                    start_line=chunk.metadata.start_line,
                    end_line=chunk.metadata.end_line,
                    chunk_index=chunk.metadata.chunk_index,
                    total_chunks=len(chunks),
                ),
                token_count=chunk.token_count,
            )
            for chunk in chunks
        ]

        return chunks

    def _discover_documents(
        self,
        root_path: Path,
        excluded_patterns: List[str],
    ) -> List[Path]:
        """
        Discover documentation files.

        Looks for: README, CONTRIBUTING, SECURITY, API docs,
        architecture docs, design docs, etc.

        Args:
            root_path: Root directory
            excluded_patterns: Patterns to exclude

        Returns:
            List of document file paths
        """
        # Document extensions and patterns
        doc_patterns = [
            "*.md",
            "*.markdown",
            "*.txt",
            "*.rst",
            "*.adoc",
            "*.asciidoc",
            "README*",
            "CONTRIBUTING*",
            "SECURITY*",
            "CHANGELOG*",
            "LICENSE*",
            "docs/**/*",
            "documentation/**/*",
        ]

        doc_files = []
        for pattern in doc_patterns:
            found = list(root_path.rglob(pattern))
            doc_files.extend(found)

        # Remove duplicates
        doc_files = list(set(doc_files))

        # Filter excluded patterns and non-files
        filtered_docs = []
        for doc_path in doc_files:
            if not doc_path.is_file():
                continue

            should_exclude = False
            relative_path = str(doc_path.relative_to(root_path))

            for pattern in excluded_patterns:
                pattern_clean = pattern.replace("**", "").replace("*", "")
                if pattern_clean in relative_path or pattern_clean in str(doc_path):
                    should_exclude = True
                    break

            if not should_exclude:
                filtered_docs.append(doc_path)

        return filtered_docs

    async def _process_document(
        self,
        doc_path: Path,
        command: IndexCodebaseCommand,
    ):
        """
        Process a documentation file.

        Args:
            doc_path: Path to document
            command: Index command with settings
        """
        try:
            # Skip binary files based on extension
            binary_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
                               '.pdf', '.zip', '.tar', '.gz', '.exe', '.bin',
                               '.woff', '.woff2', '.ttf', '.eot', '.svg'}
            if doc_path.suffix.lower() in binary_extensions:
                return

            # Read document with error handling
            try:
                content = doc_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Skip files that can't be decoded as text
                return

            # Determine document type
            relative_path = str(doc_path.relative_to(command.codebase_path))
            doc_type = self._classify_document(doc_path.name, relative_path)

            # Create document
            document = Document.create(
                path=doc_path,
                relative_path=relative_path,
                content=content,
                document_type=doc_type,
            )

            # Chunk the document
            chunks = self._chunk_document(
                content=content,
                metadata=document.metadata,
                chunk_size=command.doc_chunk_size,
            )

            # Generate embeddings in batch
            texts = [chunk.content for chunk in chunks]
            embeddings = await self.llm_service.generate_embeddings_batch(texts)

            # Add embeddings to chunks
            chunks_with_embeddings = [
                chunk.with_embedding(embedding)
                for chunk, embedding in zip(chunks, embeddings)
            ]

            # Store chunks in separate collection
            await self.vector_store.store_document_chunks(
                chunks_with_embeddings,
                collection="documents"
            )

            print(f"  Processed document: {relative_path} ({len(chunks)} chunks)")

        except Exception as e:
            print(f"  Error processing document {doc_path}: {e}")

    def _classify_document(self, filename: str, relative_path: str) -> str:
        """
        Classify document type based on filename and path.

        Args:
            filename: Name of the file
            relative_path: Relative path from root

        Returns:
            Document type classification
        """
        filename_upper = filename.upper()
        path_lower = relative_path.lower()

        # Check filename patterns
        if "README" in filename_upper:
            return "readme"
        elif "CONTRIBUTING" in filename_upper:
            return "contributing"
        elif "SECURITY" in filename_upper:
            return "security_policy"
        elif "CHANGELOG" in filename_upper:
            return "changelog"
        elif "LICENSE" in filename_upper:
            return "license"
        elif "API" in filename_upper or "api" in path_lower:
            return "api_doc"
        elif "ARCHITECTURE" in filename_upper or "architecture" in path_lower:
            return "architecture"
        elif "DESIGN" in filename_upper or "design" in path_lower:
            return "design_doc"
        elif "GUIDE" in filename_upper or "tutorial" in path_lower:
            return "guide"
        else:
            return "documentation"

    def _chunk_document(
        self,
        content: str,
        metadata: DocumentMetadata,
        chunk_size: int,
    ) -> List[DocumentChunk]:
        """
        Chunk document content by character count with overlap.

        Args:
            content: Document content
            metadata: Document metadata
            chunk_size: Characters per chunk

        Returns:
            List of document chunks
        """
        chunks = []
        chunk_index = 0
        overlap = chunk_size // 4  # 25% overlap

        start = 0
        while start < len(content):
            end = min(start + chunk_size, len(content))

            # Try to break at sentence or paragraph boundary
            if end < len(content):
                # Look for paragraph break
                para_break = content.rfind("\n\n", start, end)
                if para_break > start + chunk_size // 2:
                    end = para_break + 2
                else:
                    # Look for sentence break
                    sent_break = max(
                        content.rfind(". ", start, end),
                        content.rfind(".\n", start, end),
                        content.rfind("! ", start, end),
                        content.rfind("? ", start, end),
                    )
                    if sent_break > start + chunk_size // 2:
                        end = sent_break + 2

            chunk_content = content[start:end].strip()

            if chunk_content:  # Skip empty chunks
                chunk = DocumentChunk.create(
                    content=chunk_content,
                    metadata=metadata,
                    start_char=start,
                    end_char=end,
                    chunk_index=chunk_index,
                    total_chunks=0,  # Will be updated
                )
                chunks.append(chunk)
                chunk_index += 1

            # Move to next chunk with overlap
            start = end - overlap if end < len(content) else end

        # Update total chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks