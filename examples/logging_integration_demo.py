"""
Logging Integration POC - Demonstrates logging at 5 critical points.

This demonstrates how logging with context management would be integrated
into FalconEYE at key architectural points:

1. CLI entry point (command execution starts)
2. Indexing operation (file processing)
3. Vector store operation
4. LLM interaction
5. Error handling

Run with: python examples/logging_integration_demo.py
"""

import asyncio
import uuid
from pathlib import Path
from falconeye.infrastructure.logging import FalconEyeLogger, LogContext, logging_context


def setup_logger():
    """Initialize FalconEYE logger."""
    logger = FalconEyeLogger.get_instance(
        level="INFO",
        log_file=Path("./demo_logs/falconeye_demo.log"),
        console=True,
        rotation="daily",
        retention_days=30
    )
    return logger


async def main():
    """Demonstrate logging integration at 5 critical points."""

    # Initialize logger
    logger = setup_logger()

    # ============================================================
    # POINT 1: CLI Entry Point (Command Execution Starts)
    # ============================================================
    command_id = f"cmd-{uuid.uuid4().hex[:8]}"
    project_id = "demo-project"

    with logging_context(command_id=command_id, command="index"):
        logger.info(
            "Command execution started",
            extra={
                "path": "/path/to/codebase",
                "user": "demo_user"
            }
        )

        # ============================================================
        # POINT 2: Indexing Operation (File Processing)
        # ============================================================
        with logging_context(
            project_id=project_id,
            operation="indexing"
        ):
            logger.info("Starting file discovery")

            # Simulate file discovery
            discovered_files = ["file1.py", "file2.py", "file3.py"]
            logger.info(
                "File discovery completed",
                extra={"files_found": len(discovered_files)}
            )

            # Process each file
            for idx, file_path in enumerate(discovered_files, 1):
                with logging_context(file_path=file_path, file_index=idx):
                    logger.info("Processing file started")

                    # Simulate chunking
                    chunks_created = 5
                    logger.debug(
                        "File chunked",
                        extra={"chunks": chunks_created}
                    )

                    # ============================================================
                    # POINT 3: Vector Store Operation
                    # ============================================================
                    with logging_context(operation="vector_store"):
                        logger.info(
                            "Storing embeddings",
                            extra={"chunk_count": chunks_created}
                        )

                        # Simulate vector store operation
                        await asyncio.sleep(0.1)  # Simulate async operation

                        logger.info(
                            "Embeddings stored successfully",
                            extra={
                                "duration_ms": 100,
                                "vectors_stored": chunks_created
                            }
                        )

                    logger.info("File processing completed")

            # ============================================================
            # POINT 4: LLM Interaction (Analysis)
            # ============================================================
            with logging_context(operation="llm_analysis"):
                logger.info(
                    "Sending analysis request to LLM",
                    extra={
                        "model": "qwen3-coder:30b",
                        "chunks": 15,
                        "prompt_length": 4500
                    }
                )

                # Simulate LLM call
                await asyncio.sleep(0.2)

                logger.info(
                    "Received LLM response",
                    extra={
                        "duration_seconds": 5.2,
                        "tokens_used": 3000,
                        "findings_detected": 3
                    }
                )

            # ============================================================
            # POINT 5: Error Handling (Demonstrate exception logging)
            # ============================================================
            with logging_context(operation="error_demonstration"):
                logger.info("Demonstrating error handling")

                try:
                    # Simulate an error scenario
                    raise ValueError("Simulated error for demonstration")

                except ValueError as e:
                    logger.error(
                        "Operation failed with error",
                        exc_info=True,
                        extra={
                            "error_type": type(e).__name__,
                            "recovery_attempted": True
                        }
                    )

                    # Log recovery action
                    logger.warning(
                        "Attempting recovery",
                        extra={"retry_count": 1}
                    )

            # Final summary with metrics
            logger.info(
                "Command execution completed successfully",
                extra={
                    "metrics": {
                        "total_files": len(discovered_files),
                        "total_chunks": 15,
                        "duration_seconds": 12.5,
                        "errors_encountered": 1,
                        "errors_recovered": 1
                    }
                }
            )

    print("\n" + "="*70)
    print("LOGGING DEMO COMPLETED")
    print("="*70)
    print(f"\nCheck logs at: ./demo_logs/falconeye_demo.log")
    print("\nKey Features Demonstrated:")
    print("  1. ✅ Command execution logging at CLI entry point")
    print("  2. ✅ File processing and indexing logs")
    print("  3. ✅ Vector store operation tracking")
    print("  4. ✅ LLM interaction metrics")
    print("  5. ✅ Exception handling with stack traces")
    print("\nContext Features:")
    print("  • Automatic correlation ID propagation")
    print("  • Nested context support (operation tracking)")
    print("  • File-level context (per-file processing)")
    print("  • Metrics embedded in logs")
    print("  • Thread-safe context isolation")


if __name__ == "__main__":
    asyncio.run(main())
