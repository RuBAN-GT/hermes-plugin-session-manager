"""Directory-plugin shim for Hermes GitHub installs."""

if __package__:
    from .hermes_session_manager.plugin import register
else:
    from hermes_session_manager.plugin import register

__all__ = ["register"]
