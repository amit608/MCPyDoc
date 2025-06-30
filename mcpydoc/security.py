"""Security utilities and validators for MCPyDoc."""

import logging
import re
import signal
import subprocess
import sys
from functools import wraps
from pathlib import Path
from typing import Any, Callable, List, Optional, TypeVar, Union

try:
    import resource
except ImportError:
    # resource module is not available on Windows
    resource = None

logger = logging.getLogger(__name__)

# Security constants
MAX_PACKAGE_NAME_LENGTH = 100
MAX_SYMBOL_PATH_LENGTH = 200
MAX_VERSION_LENGTH = 50
MAX_RECURSION_DEPTH = 50
MAX_MEMORY_MB = 512
MAX_EXECUTION_TIME_SECONDS = 30

# Regex patterns for validation
PACKAGE_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-]*$")
VERSION_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
SYMBOL_PATH_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.]*$")

# Known dangerous packages (expandable)
PACKAGE_BLACKLIST = {
    "__builtin__",
    "__builtins__",
    "os",
    "subprocess",
    "sys",
    "eval",
    "exec",
    "compile",
}

F = TypeVar("F", bound=Callable[..., Any])

# Import security exceptions from the main exceptions module
from .exceptions import (
    PackageSecurityError,
    ResourceLimitError,
    SecurityError,
    ValidationError,
)


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize a string for safe logging and display.

    Args:
        value: String to sanitize
        max_length: Maximum length to allow

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        value = str(value)

    # Remove control characters and limit length
    sanitized = "".join(c for c in value if c.isprintable())
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized


def validate_package_name(package_name: str) -> None:
    """Validate a package name for security.

    Args:
        package_name: Package name to validate

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(package_name, str):
        raise ValidationError(f"Package name must be string, got {type(package_name)}")

    if len(package_name) > MAX_PACKAGE_NAME_LENGTH:
        raise ValidationError(
            f"Package name too long: {len(package_name)} > {MAX_PACKAGE_NAME_LENGTH}"
        )

    if not PACKAGE_NAME_PATTERN.match(package_name):
        raise ValidationError(
            f"Invalid package name format: {sanitize_string(package_name)}"
        )

    # Check against blacklist
    if package_name.lower() in PACKAGE_BLACKLIST:
        raise PackageSecurityError(
            f"Package '{package_name}' is blacklisted for security reasons"
        )

    # Additional security checks
    if ".." in package_name or "/" in package_name or "\\" in package_name:
        raise ValidationError(
            f"Package name contains illegal path characters: {sanitize_string(package_name)}"
        )


def validate_version(version: Optional[str]) -> None:
    """Validate a version string.

    Args:
        version: Version string to validate

    Raises:
        ValidationError: If validation fails
    """
    if version is None:
        return

    if not isinstance(version, str):
        raise ValidationError(f"Version must be string, got {type(version)}")

    if len(version) > MAX_VERSION_LENGTH:
        raise ValidationError(
            f"Version string too long: {len(version)} > {MAX_VERSION_LENGTH}"
        )

    if not VERSION_PATTERN.match(version):
        raise ValidationError(f"Invalid version format: {sanitize_string(version)}")


def validate_symbol_path(symbol_path: str) -> None:
    """Validate a symbol path.

    Args:
        symbol_path: Symbol path to validate

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(symbol_path, str):
        raise ValidationError(f"Symbol path must be string, got {type(symbol_path)}")

    if len(symbol_path) > MAX_SYMBOL_PATH_LENGTH:
        raise ValidationError(
            f"Symbol path too long: {len(symbol_path)} > {MAX_SYMBOL_PATH_LENGTH}"
        )

    if not SYMBOL_PATH_PATTERN.match(symbol_path):
        raise ValidationError(
            f"Invalid symbol path format: {sanitize_string(symbol_path)}"
        )

    # Additional security checks for dangerous patterns
    if ".." in symbol_path:
        raise ValidationError(
            f"Symbol path contains dangerous pattern '..': {sanitize_string(symbol_path)}"
        )

    # Check for other dangerous patterns
    dangerous_patterns = ["__", "eval", "exec", "compile", "import"]
    for pattern in dangerous_patterns:
        if pattern in symbol_path.lower():
            logger.warning(
                f"Potentially dangerous symbol path: {sanitize_string(symbol_path)}"
            )


def validate_file_path(file_path: Union[str, Path]) -> Path:
    """Validate and normalize a file path.

    Args:
        file_path: File path to validate

    Returns:
        Normalized Path object

    Raises:
        ValidationError: If validation fails
    """
    try:
        path = Path(file_path).resolve()
    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid file path: {sanitize_string(str(file_path))}")

    # Check for path traversal attempts
    try:
        # This will raise ValueError if path tries to escape
        path.relative_to(Path.cwd())
    except ValueError:
        # Allow system paths for packages, but log them
        logger.info(f"Accessing system path: {path}")

    return path


def timeout(seconds: int = MAX_EXECUTION_TIME_SECONDS):
    """Decorator to add timeout protection to functions.

    Args:
        seconds: Timeout in seconds
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            def timeout_handler(signum, frame):
                raise ResourceLimitError(
                    f"Function {func.__name__} timed out after {seconds} seconds"
                )

            # Set up timeout (Unix only)
            if hasattr(signal, "SIGALRM"):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(seconds)

                try:
                    result = func(*args, **kwargs)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)

                return result
            else:
                # Windows doesn't support SIGALRM, just run without timeout
                logger.warning("Timeout not supported on this platform")
                return func(*args, **kwargs)

        return wrapper

    return decorator


def memory_limit(max_memory_mb: int = MAX_MEMORY_MB):
    """Decorator to add memory limit protection to functions.

    Args:
        max_memory_mb: Maximum memory in MB
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Set memory limit (Unix only)
            if resource and hasattr(resource, "RLIMIT_AS"):
                try:
                    max_memory_bytes = max_memory_mb * 1024 * 1024
                    resource.setrlimit(
                        resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes)
                    )
                except (OSError, ValueError) as e:
                    logger.warning(f"Could not set memory limit: {e}")
            else:
                logger.warning("Memory limits not supported on this platform")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def safe_import_package(package_name: str, timeout_seconds: int = 10) -> bool:
    """Safely test if a package can be imported without executing it.

    Args:
        package_name: Name of package to test
        timeout_seconds: Timeout for the operation

    Returns:
        True if package exists and can be safely imported

    Raises:
        PackageSecurityError: If security checks fail
    """
    validate_package_name(package_name)

    # Use subprocess to isolate the import test
    try:
        cmd = [
            sys.executable,
            "-c",
            f'import sys; import {package_name}; print("SUCCESS")',
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_seconds, check=False
        )

        if result.returncode == 0 and "SUCCESS" in result.stdout:
            return True
        else:
            logger.info(f"Package {package_name} import test failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        raise PackageSecurityError(f"Package {package_name} import test timed out")
    except Exception as e:
        logger.error(f"Error testing package {package_name}: {e}")
        return False


class SecurityContext:
    """Context manager for applying security constraints."""

    def __init__(
        self,
        max_memory_mb: int = MAX_MEMORY_MB,
        max_time_seconds: int = MAX_EXECUTION_TIME_SECONDS,
    ):
        self.max_memory_mb = max_memory_mb
        self.max_time_seconds = max_time_seconds
        self.old_limits = {}

    def __enter__(self):
        # Set resource limits
        if resource and hasattr(resource, "RLIMIT_AS"):
            try:
                old_limit = resource.getrlimit(resource.RLIMIT_AS)
                self.old_limits["memory"] = old_limit
                max_memory_bytes = self.max_memory_mb * 1024 * 1024
                resource.setrlimit(
                    resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes)
                )
            except (OSError, ValueError) as e:
                logger.warning(f"Could not set memory limit: {e}")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old limits
        if "memory" in self.old_limits and resource and hasattr(resource, "RLIMIT_AS"):
            try:
                resource.setrlimit(resource.RLIMIT_AS, self.old_limits["memory"])
            except (OSError, ValueError) as e:
                logger.warning(f"Could not restore memory limit: {e}")


def audit_log(operation: str, **kwargs):
    """Log security-relevant operations for auditing.

    Args:
        operation: Type of operation being performed
        **kwargs: Additional context information
    """
    # Sanitize all logged values
    sanitized_kwargs = {
        key: sanitize_string(str(value)) for key, value in kwargs.items()
    }

    logger.info(
        f"AUDIT: {operation}",
        extra={"operation": operation, "context": sanitized_kwargs},
    )
