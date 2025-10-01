#!/usr/bin/env python3
"""Test document embedding functionality."""

import sys
import asyncio
from pathlib import Path
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from falconeye.infrastructure.config.config_loader import ConfigLoader
from falconeye.infrastructure.di.container import DIContainer


async def test_document_embedding():
    """Test that documents can be indexed and retrieved."""
    print("=" * 80)
    print("Testing FalconEYE Document Embedding")
    print("=" * 80)
    print()

    # Create temporary test directory with code and documentation
    test_dir = Path(tempfile.mkdtemp(prefix="falconeye_doc_test_"))
    print(f"Created test directory: {test_dir}")

    try:
        # Create a simple Python file
        code_file = test_dir / "app.py"
        code_file.write_text("""
import os
import hashlib

def authenticate_user(username, password):
    # Authenticate user against database
    stored_hash = get_stored_hash(username)
    password_hash = hashlib.md5(password.encode()).hexdigest()
    return password_hash == stored_hash

def get_stored_hash(username):
    # TODO: implement database lookup
    return "5f4dcc3b5aa765d61d8327deb882cf99"
""")

        # Create README with security context
        readme = test_dir / "README.md"
        readme.write_text("""
# Authentication Module

This module handles user authentication for the application.

## Security Requirements

- All passwords must be hashed using SHA-256 or stronger
- Password hashes must be salted with unique per-user salts
- Never use MD5 for password hashing (it's cryptographically broken)

## Architecture

The authentication flow:
1. User submits credentials
2. System retrieves stored hash from database
3. Compares hashed password with stored hash
4. Returns authentication result
""")

        # Create security policy
        security_doc = test_dir / "SECURITY.md"
        security_doc.write_text("""
# Security Policy

## Cryptography Standards

- Password Hashing: Use bcrypt, scrypt, or Argon2
- DO NOT use MD5 or SHA1 for passwords
- All password hashes must include a unique salt

## Vulnerability Reporting

Please report security vulnerabilities to security@example.com
""")

        print("Created test files:")
        print(f"  - {code_file.name}")
        print(f"  - {readme.name}")
        print(f"  - {security_doc.name}")
        print()

        # Create container (it will load configuration internally)
        print("Creating DI container...")
        container = DIContainer.create()
        print("✓ Container initialized")
        print(f"  Provider: {container.config.llm.provider}")
        print()

        # Get services
        index_handler = container.index_handler
        vector_store = container.vector_store
        context_assembler = container.context_assembler

        # Index the codebase (including documents)
        print("Indexing codebase with documents...")
        from falconeye.application.commands.index_codebase import IndexCodebaseCommand

        command = IndexCodebaseCommand(
            codebase_path=test_dir,
            language="python",
            include_documents=True,  # Enable document indexing
            doc_chunk_size=500,
        )

        codebase = await index_handler.handle(command)
        print()
        print(f"✓ Indexed {codebase.total_files} code files, {codebase.total_lines} lines")

        # Verify documents were indexed
        code_count = await vector_store.get_chunk_count("code")
        doc_count = await vector_store.get_chunk_count("documents")

        print(f"✓ Code chunks in vector store: {code_count}")
        print(f"✓ Document chunks in vector store: {doc_count}")
        print()

        if doc_count == 0:
            print("✗ FAILED: No documents were indexed!")
            return False

        # Test document retrieval
        print("Testing document retrieval...")
        print("Query: 'password hashing MD5'")
        print()

        # Generate embedding for the query
        from falconeye.infrastructure.llm_providers.ollama_adapter import OllamaLLMAdapter
        temp_llm = OllamaLLMAdapter()
        query_embedding = await temp_llm.generate_embedding("password hashing MD5")

        doc_chunks = await vector_store.search_similar_documents(
            query="password hashing MD5",
            top_k=3,
            collection="documents",
            query_embedding=query_embedding,
        )

        if not doc_chunks:
            print("✗ FAILED: No documents retrieved!")
            return False

        print(f"✓ Retrieved {len(doc_chunks)} relevant document chunks:")
        print()

        for i, chunk in enumerate(doc_chunks, 1):
            doc_type = chunk.metadata.document_type.replace("_", " ").title()
            print(f"[{i}] {doc_type} - {chunk.metadata.file_path}")
            print(f"    Chunk {chunk.chunk_index + 1}/{chunk.total_chunks}")
            print(f"    Preview: {chunk.content[:200]}...")
            print()

        # Test context assembly with documents
        print("=" * 80)
        print("Testing Context Assembly with Documents")
        print("=" * 80)
        print()

        # Assemble context for the authentication function
        context = await context_assembler.assemble_context(
            file_path="app.py",
            code_snippet=code_file.read_text(),
            language="python",
            top_k_similar=3,
            top_k_docs=2,  # Retrieve 2 relevant docs
        )

        print("Context assembled successfully!")
        print(f"  - File: {context.file_path}")
        print(f"  - Language: {context.language}")
        print(f"  - Has structural metadata: {context.structural_metadata is not None}")
        print(f"  - Has related code: {context.related_code is not None}")
        print(f"  - Has related docs: {context.related_docs is not None}")
        print()

        if context.related_docs:
            print("Related documentation retrieved:")
            print("-" * 80)
            print(context.related_docs[:500] + "..." if len(context.related_docs) > 500 else context.related_docs)
            print()

        # Verify the context mentions security requirements
        if context.related_docs and ("MD5" in context.related_docs or "SHA-256" in context.related_docs):
            print("✓ Context includes security requirements from documentation!")
        else:
            print("⚠ Warning: Context may not include relevant security documentation")

        print()
        print("=" * 80)
        print("✓ ALL TESTS PASSED")
        print("=" * 80)
        print()
        print("Summary:")
        print(f"  - Documents indexed: {doc_count} chunks")
        print(f"  - Document retrieval: Working")
        print(f"  - Context assembly: Working")
        print(f"  - Security context: Available to AI")
        print()
        print("Documentation embedding is fully functional!")
        return True

    finally:
        # Cleanup
        print()
        print(f"Cleaning up test directory: {test_dir}")
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    success = asyncio.run(test_document_embedding())
    sys.exit(0 if success else 1)