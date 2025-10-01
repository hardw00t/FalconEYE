"""
Tests for circuit breaker pattern.

Following TDD methodology - comprehensive tests for circuit breaker behavior.
"""

import pytest
import asyncio
import time
from unittest.mock import patch

from falconeye.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    CircuitBreakerError
)


class TestCircuitBreaker:
    """Test suite for circuit breaker."""

    @pytest.mark.asyncio
    async def test_closed_state_allows_calls(self):
        """Test that CLOSED state allows calls through."""
        breaker = CircuitBreaker(
            name="test_service",
            config=CircuitBreakerConfig(failure_threshold=3)
        )

        @breaker.protect
        async def successful_call():
            return "success"

        result = await successful_call()

        assert result == "success"
        assert breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self):
        """Test that circuit opens after failure threshold."""
        breaker = CircuitBreaker(
            name="test_service",
            config=CircuitBreakerConfig(failure_threshold=3)
        )

        call_count = 0

        @breaker.protect
        async def failing_call():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Service unavailable")

        # Make failures up to threshold
        for i in range(3):
            with pytest.raises(ConnectionError):
                await failing_call()

        # Circuit should now be OPEN
        assert breaker.state == CircuitBreakerState.OPEN
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_open_state_blocks_calls(self):
        """Test that OPEN state blocks calls."""
        breaker = CircuitBreaker(
            name="test_service",
            config=CircuitBreakerConfig(failure_threshold=2, timeout=60)
        )

        @breaker.protect
        async def call():
            raise ConnectionError("Fail")

        # Trigger circuit to open
        for i in range(2):
            with pytest.raises(ConnectionError):
                await call()

        assert breaker.state == CircuitBreakerState.OPEN

        # Next call should be blocked with CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            await call()

    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self):
        """Test that circuit enters HALF_OPEN after timeout."""
        breaker = CircuitBreaker(
            name="test_service",
            config=CircuitBreakerConfig(failure_threshold=2, timeout=0.1)  # 100ms timeout
        )

        @breaker.protect
        async def call():
            return "success"

        # Open the circuit
        for i in range(2):
            try:
                raise ConnectionError("Fail")
            except ConnectionError as e:
                breaker._record_failure(e)

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Check state should transition to HALF_OPEN
        state = breaker.state
        assert state == CircuitBreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_closes_on_success(self):
        """Test that HALF_OPEN closes after success threshold."""
        breaker = CircuitBreaker(
            name="test_service",
            config=CircuitBreakerConfig(
                failure_threshold=2,
                success_threshold=2,
                timeout=0.1
            )
        )

        @breaker.protect
        async def call():
            return "success"

        # Open the circuit
        for i in range(2):
            try:
                raise ConnectionError("Fail")
            except ConnectionError as e:
                breaker._record_failure(e)

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for timeout and transition to HALF_OPEN
        await asyncio.sleep(0.15)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        # Make successful calls to close circuit
        await call()  # First success
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        await call()  # Second success - should close
        assert breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_reopens_on_failure(self):
        """Test that HALF_OPEN reopens immediately on failure."""
        breaker = CircuitBreaker(
            name="test_service",
            config=CircuitBreakerConfig(failure_threshold=2, timeout=0.1)
        )

        call_count = 0

        @breaker.protect
        async def call():
            nonlocal call_count
            call_count += 1
            if call_count > 2:
                raise ConnectionError("Still failing")
            raise ConnectionError("Fail")

        # Open the circuit
        for i in range(2):
            with pytest.raises(ConnectionError):
                await call()

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        # Failure in HALF_OPEN should reopen circuit
        with pytest.raises(ConnectionError):
            await call()

        assert breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_excluded_exceptions_dont_count(self):
        """Test that excluded exceptions don't count as failures."""
        breaker = CircuitBreaker(
            name="test_service",
            config=CircuitBreakerConfig(
                failure_threshold=2,
                exclude_exceptions=(ValueError,)
            )
        )

        @breaker.protect
        async def call_with_value_error():
            raise ValueError("Business logic error")

        # ValueError should not count toward failure threshold
        for i in range(5):
            with pytest.raises(ValueError):
                await call_with_value_error()

        # Circuit should still be CLOSED
        assert breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_reset_clears_state(self):
        """Test that reset() clears circuit breaker state."""
        breaker = CircuitBreaker(
            name="test_service",
            config=CircuitBreakerConfig(failure_threshold=2)
        )

        @breaker.protect
        async def failing_call():
            raise ConnectionError("Fail")

        # Open the circuit
        for i in range(2):
            with pytest.raises(ConnectionError):
                await failing_call()

        assert breaker.state == CircuitBreakerState.OPEN

        # Reset
        breaker.reset()

        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker._failure_count == 0

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """Test that successful calls reset failure count."""
        breaker = CircuitBreaker(
            name="test_service",
            config=CircuitBreakerConfig(failure_threshold=3)
        )

        call_count = 0

        @breaker.protect
        async def intermittent_failure():
            nonlocal call_count
            call_count += 1
            # Fail twice, then succeed, then fail twice
            if call_count in [1, 2, 4, 5]:
                raise ConnectionError("Fail")
            return "success"

        # Two failures
        for i in range(2):
            with pytest.raises(ConnectionError):
                await intermittent_failure()

        # Success should reset count
        result = await intermittent_failure()
        assert result == "success"

        # Two more failures should not open circuit (count was reset)
        for i in range(2):
            with pytest.raises(ConnectionError):
                await intermittent_failure()

        # Circuit should still be CLOSED (only 2 consecutive failures)
        assert breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_concurrent_calls_thread_safety(self):
        """Test that circuit breaker is thread-safe under concurrent calls."""
        breaker = CircuitBreaker(
            name="test_service",
            config=CircuitBreakerConfig(failure_threshold=10)
        )

        call_count = 0

        @breaker.protect
        async def concurrent_call(should_fail):
            nonlocal call_count
            call_count += 1
            if should_fail:
                raise ConnectionError("Fail")
            return "success"

        # Make many concurrent calls
        tasks = []
        for i in range(20):
            # Half will fail, half will succeed
            should_fail = i % 2 == 0
            tasks.append(concurrent_call(should_fail))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        successes = sum(1 for r in results if r == "success")
        failures = sum(1 for r in results if isinstance(r, ConnectionError))

        assert successes == 10
        assert failures == 10
        assert call_count == 20

    def test_synchronous_protect(self):
        """Test circuit breaker with synchronous functions."""
        breaker = CircuitBreaker(
            name="test_service",
            config=CircuitBreakerConfig(failure_threshold=2)
        )

        @breaker.protect_sync
        def sync_call():
            return "success"

        result = sync_call()
        assert result == "success"

        @breaker.protect_sync
        def failing_sync_call():
            raise ConnectionError("Fail")

        # Open circuit
        for i in range(2):
            with pytest.raises(ConnectionError):
                failing_sync_call()

        assert breaker.state == CircuitBreakerState.OPEN

        # Should block
        with pytest.raises(CircuitBreakerError):
            failing_sync_call()
