"""TransactionStatus reference for Text-to-SQL prompts.

Groups all status values by pipeline phase so Claude can correctly identify
failure statuses, in-progress states, and terminal states without guessing.
Reuses the existing TransactionStatus enum from app.models.remittance.
"""

from app.models.remittance import FAILED_STATUSES, TERMINAL_STATUSES, TransactionStatus

_PHASE_GROUPS: list[tuple[str, list[TransactionStatus]]] = [
    ("Payment phase", [
        TransactionStatus.PAYMENT_VALIDATED,
        TransactionStatus.PAYMENT_ACCEPTED,
        TransactionStatus.PAYMENT_PENDING,
        TransactionStatus.PAYMENT_RESERVED,
        TransactionStatus.PAYMENT_FAILED,
        TransactionStatus.PAYMENT_VALIDATION_FAILED,
        TransactionStatus.PAYMENT_RESERVATION_FAILED,
        TransactionStatus.PAYMENT_ACCEPTANCE_FAILED,
    ]),
    ("SOF (Source of Funds) phase", [
        TransactionStatus.SOF_PAY_PENDING,
        TransactionStatus.SOF_PAY_COMPLETED,
        TransactionStatus.SOF_PAY_FAILED,
    ]),
    ("Remittance phase", [
        TransactionStatus.TRANSACTION_SUBMITTED,
        TransactionStatus.TRANSACTION_IN_PROGRESS,
        TransactionStatus.TRANSACTION_SUCCESS,
        TransactionStatus.TRANSACTION_COMPLETED,
        TransactionStatus.TRANSACTION_CONFIRMED,
        TransactionStatus.TRANSACTION_FAILED,
        TransactionStatus.TRANSACTION_DECLINED,
        TransactionStatus.TRANSACTION_ON_HOLD,
        TransactionStatus.TRANSACTION_CANCELLED,
        TransactionStatus.TRANSACTION_EXPIRED,
    ]),
    ("Refund phase", [
        TransactionStatus.REFUND_REQUIRED,
        TransactionStatus.PAYMENT_REFUND_REQUIRED,
        TransactionStatus.SOF_REFUND_REQUIRED,
        TransactionStatus.REFUNDED,
        TransactionStatus.REFUND_FAILED,
        TransactionStatus.REFUND_IN_PROGRESS,
    ]),
    ("Fraud", [
        TransactionStatus.FRAUD_CHECK_FAILED,
        TransactionStatus.FRAUD_CHECK_DECLINED,
        TransactionStatus.FRAUD_CHECK_TIMEOUT,
    ]),
    ("Other", [
        TransactionStatus.PENDING,
        TransactionStatus.INITIATED,
    ]),
]


def get_status_ref() -> str:
    """Return a formatted status reference string for injection into LLM prompts."""
    failed_values = sorted(s.value for s in FAILED_STATUSES)
    terminal_values = sorted(s.value for s in TERMINAL_STATUSES)

    lines = ["=== TRANSACTION STATUS REFERENCE ===", ""]
    for phase, statuses in _PHASE_GROUPS:
        lines.append(f"{phase}:")
        for s in statuses:
            lines.append(f"  {s.value}")
        lines.append("")

    lines.append("Failed statuses (use for failure rate / failure count queries):")
    for v in failed_values:
        lines.append(f"  {v}")
    lines.append("")

    lines.append("Terminal statuses (transaction is complete — no further processing):")
    for v in terminal_values:
        lines.append(f"  {v}")
    lines.append("")

    lines.append("=====================================")
    return "\n".join(lines)
