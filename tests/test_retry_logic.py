"""
Tests for retry logic with exponential backoff.

Following TDD methodology - comprehensive tests for retry behavior.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import time

from falconeye.infrastructure.resilience import retry_with_backoff, RetryConfig


class TestRetryLogic:
    """Test suite for retry logic."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Test that successful calls don't retry."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_retries=3))
        async def successful_call():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_call()

        assert result == "success"
        assert call_count == 1, "Should only call once for successful operation"

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self):
        """Test retry on connection errors."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_retries=3, initial_delay=0.01))
        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success after retries"

        result = await failing_then_success()

        assert result == "success after retries"
        assert call_count == 3, "Should retry twice before succeeding"

    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """Test that all retries are exhausted before raising."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_retries=2, initial_delay=0.01))
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            await always_fails()

        assert call_count == 3, "Should try once + 2 retries"

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that backoff delays increase exponentially."""
        call_times = []

        @retry_with_backoff(RetryConfig(
            max_retries=3,
            initial_delay=0.1,
            exponential_base=2.0,
            jitter=0.0  # Disable jitter for predictable timing
        ))
        async def failing_call():
            call_times.append(time.time())
            raise ConnectionError("Fail")

        with pytest.raises(ConnectionError):
            await failing_call()

        # Verify exponential backoff
        assert len(call_times) == 4  # Initial + 3 retries

        # Check delays between attempts (approximately 0.1, 0.2, 0.4)
        delays = [call_times[i+1] - call_times[i] for i in range(len(call_times)-1)]

        # Allow some tolerance for timing
        assert 0.08 < delays[0] < 0.15, f"First delay should be ~0.1s, got {delays[0]}"
        assert 0.15 < delays[1] < 0.25, f"Second delay should be ~0.2s, got {delays[1]}"
        assert 0.35 < delays[2] < 0.45, f"Third delay should be ~0.4s, got {delays[2]}"

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are raised immediately."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_retries=3, initial_delay=0.01))
        async def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not a retryable error")

        with pytest.raises(ValueError):
            await raises_value_error()

        assert call_count == 1, "Should not retry non-retryable exceptions"

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        call_times = []

        @retry_with_backoff(RetryConfig(
            max_retries=5,
            initial_delay=1.0,
            max_delay=2.0,  # Cap at 2 seconds
            exponential_base=2.0,
            jitter=0.0
        ))
        async def failing_call():
            call_times.append(time.time())
            raise ConnectionError("Fail")

        with pytest.raises(ConnectionError):
            await failing_call()

        # Later delays should be capped at max_delay
        delays = [call_times[i+1] - call_times[i] for i in range(len(call_times)-1)]

        # Delays should be: 1.0, 2.0 (capped), 2.0 (capped), 2.0 (capped), 2.0 (capped)
        assert delays[0] < 1.5, "First delay should be ~1.0s"
        assert all(1.8 < d < 2.2 for d in delays[1:]), "Later delays should be capped at ~2.0s"

    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delays."""
        delays_set1 = []
        delays_set2 = []

        async def measure_delays():
            call_times = []

            @retry_with_backoff(RetryConfig(
                max_retries=2,
                initial_delay=0.1,
                exponential_base=2.0,
                jitter=0.5  # 50% jitter
            ))
            async def failing_call():
                call_times.append(time.time())
                raise ConnectionError("Fail")

            try:
                await failing_call()
            except ConnectionError:
                pass

            return [call_times[i+1] - call_times[i] for i in range(len(call_times)-1)]

        # Run twice to get different jitter values
        delays_set1 = await measure_delays()
        delays_set2 = await measure_delays()

        # At least one delay should be different due to jitter
        # (with 50% jitter, very unlikely to be exactly the same)
        assert delays_set1 != delays_set2, "Jitter should produce different delays"

    @pytest.mark.asyncio
    async def test_custom_retryable_exceptions(self):
        """Test custom retryable exception types."""
        call_count = 0

        class CustomError(Exception):
            pass

        @retry_with_backoff(RetryConfig(
            max_retries=2,
            initial_delay=0.01,
            retryable_exceptions=(CustomError, ConnectionError)
        ))
        async def custom_failure():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise CustomError("Custom error")
            return "success"

        result = await custom_failure()

        assert result == "success"
        assert call_count == 2, "Should retry on custom exception"

    @pytest.mark.asyncio
    async def test_timeout_error_is_retryable(self):
        """Test that TimeoutError is retried by default."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_retries=2, initial_delay=0.01))
        async def timeout_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Timeout")
            return "success"

        result = await timeout_then_success()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_os_error_is_retryable(self):
        """Test that OSError is retried by default."""
        call_count = 0

        @retry_with_backoff(RetryConfig(max_retries=2, initial_delay=0.01))
        async def os_error_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("OS error")
            return "success"

        result = await os_error_then_success()

        assert result == "success"
        assert call_count == 2
