"""
Custom exceptions for odoo-bootstrap.
"""


class BootstrapError(Exception):
    """Base exception for all odoo-bootstrap errors."""


class ConfigurationError(BootstrapError):
    """Raised when configuration is invalid or missing."""


class DockerError(BootstrapError):
    """Raised when a Docker operation fails."""


class GitError(BootstrapError):
    """Raised when a Git operation fails."""


class DatabaseError(BootstrapError):
    """Raised when a database operation fails."""


class ProjectError(BootstrapError):
    """Raised for project-level errors."""


class VersionError(BootstrapError):
    """Raised for unsupported or incompatible Odoo version."""


class BackupError(BootstrapError):
    """Raised when backup or restore fails."""


class DependencyError(BootstrapError):
    """Raised when a required system dependency is missing."""
