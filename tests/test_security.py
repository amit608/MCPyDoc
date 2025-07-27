"""Security tests for MCPyDoc.

Note: Many of these tests are designed to validate that security violations
are properly caught and raise appropriate exceptions. The tests use pytest.raises()
to verify that ValidationError, PackageSecurityError, and other security exceptions
are raised when they should be. This is the expected and correct behavior.
"""

import signal
from unittest.mock import MagicMock, patch

import pytest

from mcpydoc.exceptions import (
    PackageSecurityError,
    ResourceLimitError,
    ValidationError,
)
from mcpydoc.security import (
    SecurityContext,
    audit_log,
    memory_limit,
    safe_import_package,
    sanitize_string,
    timeout,
    validate_file_path,
    validate_package_name,
    validate_symbol_path,
    validate_version,
)


class TestInputValidation:
    """Test input validation functions."""

    def test_validate_package_name_valid(self):
        """Test valid package names."""
        valid_names = [
            "requests",
            "django-rest-framework",
            "numpy",
            "Pillow",
            "package_name",
            "package.subpackage",
        ]
        for name in valid_names:
            validate_package_name(name)  # Should not raise

    def test_validate_package_name_invalid(self):
        """Test invalid package names."""
        invalid_names = [
            "",  # Empty
            "a" * 101,  # Too long
            "123invalid",  # Starts with number
            "package/name",  # Contains slash
            "package\\name",  # Contains backslash
            "package..name",  # Contains double dots
            "../malicious",  # Path traversal
            "package name",  # Contains space
            "package\nname",  # Contains newline
        ]
        for name in invalid_names:
            with pytest.raises((ValidationError, PackageSecurityError)):
                validate_package_name(name)

    def test_validate_package_name_blacklisted(self):
        """Test blacklisted package names."""
        blacklisted = ["os", "subprocess", "sys", "eval", "exec"]
        for name in blacklisted:
            with pytest.raises(PackageSecurityError):
                validate_package_name(name)

    def test_validate_version_valid(self):
        """Test valid version strings."""
        valid_versions = [
            None,  # None should be allowed
            "1.0.0",
            "2.1.3",
            "1.0.0a1",
            "1.0.0.dev1",
            "1.0.0rc1",
        ]
        for version in valid_versions:
            validate_version(version)  # Should not raise

    def test_validate_version_invalid(self):
        """Test invalid version strings."""
        invalid_versions = [
            "",  # Empty
            "a" * 51,  # Too long
            "version with spaces",
            "version/with/slashes",
            "version\nwith\nnewlines",
        ]
        for version in invalid_versions:
            with pytest.raises(ValidationError):
                validate_version(version)

    def test_validate_symbol_path_valid(self):
        """Test valid symbol paths."""
        valid_paths = [
            "function_name",
            "ClassName",
            "module.function",
            "package.module.Class",
            "_private_function",
            "function123",
        ]
        for path in valid_paths:
            validate_symbol_path(path)  # Should not raise

    def test_validate_symbol_path_invalid(self):
        """Test invalid symbol paths."""
        invalid_paths = [
            "",  # Empty
            "a" * 201,  # Too long
            "123invalid",  # Starts with number
            "symbol with spaces",
            "symbol/with/slashes",
            "symbol\nwith\nnewlines",
            "symbol..path",  # Double dots
        ]
        for path in invalid_paths:
            with pytest.raises(ValidationError):
                validate_symbol_path(path)

    def test_sanitize_string(self):
        """Test string sanitization."""
        # Test normal string
        assert sanitize_string("normal string") == "normal string"

        # Test string with control characters
        assert sanitize_string("string\x00with\x01control") == "stringwithcontrol"

        # Test long string truncation
        long_string = "a" * 1500
        result = sanitize_string(long_string)
        assert len(result) == 1003  # 1000 + "..."
        assert result.endswith("...")

        # Test non-string input
        assert sanitize_string(12345) == "12345"


class TestResourceLimits:
    """Test resource limit decorators."""

    def test_timeout_decorator_success(self):
        """Test timeout decorator with successful execution."""

        @timeout(1)
        def quick_function():
            return "success"

        result = quick_function()
        assert result == "success"

    @pytest.mark.skipif(
        not hasattr(signal, "SIGALRM"), reason="SIGALRM not available on Windows"
    )
    def test_timeout_decorator_timeout(self):
        """Test timeout decorator with timeout."""
        import time

        @timeout(1)
        def slow_function():
            time.sleep(2)
            return "should not reach"

        with pytest.raises(ResourceLimitError):
            slow_function()

    def test_memory_limit_decorator(self):
        """Test memory limit decorator."""

        @memory_limit(100)
        def test_function():
            return "success"

        # Should execute without error (actual memory limiting is platform-dependent)
        result = test_function()
        assert result == "success"


class TestSecurityContext:
    """Test SecurityContext context manager."""

    def test_security_context(self):
        """Test SecurityContext usage."""
        with SecurityContext(max_memory_mb=100, max_time_seconds=30):
            # Should execute without error
            pass


class TestPackageImportSafety:
    """Test safe package import functionality."""

    @patch("subprocess.run")
    def test_safe_import_package_success(self, mock_run):
        """Test successful safe package import."""
        mock_run.return_value = MagicMock(returncode=0, stdout="SUCCESS\n", stderr="")

        result = safe_import_package("json")
        assert result is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_safe_import_package_failure(self, mock_run):
        """Test failed safe package import."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'nonexistent'",
        )

        result = safe_import_package("nonexistent")
        assert result is False

    @patch("subprocess.run")
    def test_safe_import_package_timeout(self, mock_run):
        """Test safe package import timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("python", 10)

        with pytest.raises(PackageSecurityError):
            safe_import_package("malicious_package")

    def test_safe_import_package_invalid_name(self):
        """Test safe package import with invalid name."""
        with pytest.raises(ValidationError):
            safe_import_package("../invalid")


class TestAuditLogging:
    """Test audit logging functionality."""

    @patch("mcpydoc.security.logger")
    def test_audit_log(self, mock_logger):
        """Test audit logging."""
        audit_log("test_operation", package="test", version="1.0")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "AUDIT: test_operation" in call_args[0][0]


class TestPathValidation:
    """Test file path validation."""

    def test_validate_file_path_valid(self):
        """Test valid file path."""
        from pathlib import Path

        # Test with current directory file
        result = validate_file_path("test.py")
        assert isinstance(result, Path)

    def test_validate_file_path_invalid(self):
        """Test invalid file path."""
        with pytest.raises(ValidationError):
            validate_file_path("invalid\0path")


class TestSecurityIntegration:
    """Integration tests for security features."""

    def test_validation_chain(self):
        """Test validation of multiple inputs in sequence."""
        # Should all pass
        validate_package_name("requests")
        validate_version("2.25.1")
        validate_symbol_path("Session.get")

        # Test with invalid inputs
        with pytest.raises(ValidationError):
            validate_package_name("invalid..package")

        with pytest.raises(ValidationError):
            validate_version("invalid version string")

        with pytest.raises(ValidationError):
            validate_symbol_path("invalid symbol path")

    def test_security_error_hierarchy(self):
        """Test security exception hierarchy."""
        # ValidationError should be a SecurityError
        try:
            validate_package_name("")
        except Exception as e:
            assert isinstance(e, ValidationError)
            from mcpydoc.exceptions import SecurityError

            assert isinstance(e, SecurityError)

    def test_sanitization_in_error_messages(self):
        """Test that error messages are sanitized."""
        malicious_input = "malicious\x00\x01input\nwith\rcontrol"

        try:
            validate_package_name(malicious_input)
        except ValidationError as e:
            # Error message should not contain control characters
            error_str = str(e)
            assert "\x00" not in error_str
            assert "\x01" not in error_str
            assert "\n" not in error_str or "Invalid package name format" in error_str


class TestSecurityConstants:
    """Test security constants and limits."""

    def test_security_limits(self):
        """Test that security limits are reasonable."""
        from mcpydoc.security import (
            MAX_EXECUTION_TIME_SECONDS,
            MAX_MEMORY_MB,
            MAX_PACKAGE_NAME_LENGTH,
            MAX_SYMBOL_PATH_LENGTH,
            MAX_VERSION_LENGTH,
        )

        # Verify limits are reasonable
        assert MAX_PACKAGE_NAME_LENGTH == 100
        assert MAX_SYMBOL_PATH_LENGTH == 200
        assert MAX_VERSION_LENGTH == 50
        assert MAX_MEMORY_MB == 512
        assert MAX_EXECUTION_TIME_SECONDS == 30

    def test_regex_patterns(self):
        """Test regex patterns for validation."""
        from mcpydoc.security import (
            PACKAGE_NAME_PATTERN,
            SYMBOL_PATH_PATTERN,
            VERSION_PATTERN,
        )

        # Test package name pattern
        assert PACKAGE_NAME_PATTERN.match("valid_package")
        assert not PACKAGE_NAME_PATTERN.match("123invalid")

        # Test version pattern
        assert VERSION_PATTERN.match("1.0.0")
        assert not VERSION_PATTERN.match("invalid version")

        # Test symbol path pattern
        assert SYMBOL_PATH_PATTERN.match("valid_symbol")
        assert not SYMBOL_PATH_PATTERN.match("123invalid")
