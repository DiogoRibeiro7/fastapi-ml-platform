import logging

audit_logger = logging.getLogger("audit")


def record_audit_event(action: str, outcome: str, **fields: object) -> None:
    """Emit a structured audit event for a security-relevant action.

    Audit events go to the dedicated "audit" logger and always carry an action
    and an outcome. The active correlation id is attached by the logging filter,
    so audit lines can be tied back to the originating request.

    Field names must avoid reserved LogRecord attributes (for example use
    "model_name", not "name"), which the logging module refuses to overwrite.
    """

    audit_logger.info(
        action,
        extra={"audit": True, "action": action, "outcome": outcome, **fields},
    )
