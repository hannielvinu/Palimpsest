from decimal import Decimal

from ..pipeline.evidence import INCONSISTENCY, finding


def check(fields):
    if not all(fields.get(key, {}).get("normalized") is not None for key in ("gross", "deductions", "net")):
        return None
    gross, deductions, net = (Decimal(fields[key]["normalized"]) for key in ("gross", "deductions", "net"))
    expected = gross - deductions
    if abs(expected - net) > Decimal("1.00"):
        return finding("arithmetic", INCONSISTENCY, "Gross minus deductions differs from net pay.", fields["net"],
                       method="Decimal arithmetic with INR 1 tolerance", limits="Some templates omit reimbursements or adjustments.",
                       confidence=min(fields[key]["confidence"] for key in ("gross", "deductions", "net")),
                       values={"expected": str(expected), "reported": str(net)}, related=[fields["gross"], fields["deductions"]], layer="fields")
