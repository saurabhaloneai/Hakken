import time
import random
from typing import Callable, TypeVar, Any

T = TypeVar('T')

RETRYABLE_ERRORS = (
    "connection",
    "timeout",
    "rate limit",
    "503",
    "502",
    "500",
    "network",
    "overloaded",
)


def is_retryable(error: Exception) -> bool:
    error_str = str(error).lower()
    return any(err in error_str for err in RETRYABLE_ERRORS)


def calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    delay = base_delay * (2 ** attempt)
    jitter = delay * 0.25 * (2 * random.random() - 1)
    return min(delay + jitter, max_delay)


def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    should_retry: Callable[[Exception], bool] = is_retryable
) -> T:
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_error = e
            
            if not should_retry(e) or attempt == max_retries - 1:
                raise Exception(f"Operation failed: {str(e)}")
            
            delay = calculate_backoff(attempt, base_delay, max_delay)
            time.sleep(delay)
    
    raise Exception(f"Operation failed after {max_retries} retries: {str(last_error)}")
