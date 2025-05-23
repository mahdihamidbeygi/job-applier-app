"""
Logging utilities for consistent logging across the application.
"""

import functools
import logging
import time
import traceback
from typing import Any, Callable, Dict, Optional, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: The name of the logger (usually __name__)

    Returns:
        logging.Logger: Configured logger
    """
    return logging.getLogger(name)


def log_execution_time(logger: Optional[logging.Logger] = None) -> Callable[[F], F]:
    """
    Decorator to log the execution time of a function.

    Args:
        logger: Optional logger to use (if None, a logger will be created with function's module name)

    Returns:
        Function decorator
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Use provided logger or create one
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)

            start_time = time.time()
            result = None
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                logger.debug(f"Function '{func.__name__}' executed in {execution_time:.4f} seconds")

        return cast(F, wrapper)

    return decorator


def log_exceptions(
    logger: Optional[logging.Logger] = None, level: int = logging.ERROR, reraise: bool = True
) -> Callable[[F], F]:
    """
    Decorator to log exceptions raised in a function.

    Args:
        logger: Optional logger to use (if None, a logger will be created with function's module name)
        level: Logging level to use (default: logging.ERROR)
        reraise: Whether to reraise the exception after logging (default: True)

    Returns:
        Function decorator
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Use provided logger or create one
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)

            try:
                return func(*args, **kwargs)
            except Exception as e:
                tb_str = traceback.format_exc()
                logger.log(level, f"Exception in {func.__name__}: {str(e)}\n{tb_str}")
                if reraise:
                    raise

        return cast(F, wrapper)

    return decorator


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that prepends a context prefix to all log messages.

    Args:
        logger: The logger to adapt
        prefix: The prefix to add to all log messages
        extra: Additional context to pass to logger
    """

    def __init__(self, logger: logging.Logger, prefix: str, extra: Optional[Dict[str, Any]] = None):
        super().__init__(logger, extra or {})
        self.prefix = prefix

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add prefix to message"""
        return f"[{self.prefix}] {msg}", kwargs


def get_prefixed_logger(name: str, prefix: str) -> LoggerAdapter:
    """
    Get a logger with a prefix added to all messages.

    Args:
        name: The name of the logger
        prefix: The prefix to add to all log messages

    Returns:
        LoggerAdapter: A logger adapter that prepends the prefix to all messages
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, prefix)
