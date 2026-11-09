import re

TYPES = {
    "PAN-style card": ["pan card", "permanent account number", "income tax department"],
    "ID proof": ["identity proof", "identity card", "id number", "date of birth"],
    "Salary slip": ["salary slip", "payslip", "gross pay", "deductions", "net pay"],
    "Bank statement": ["bank statement", "account number", "salary credit", "credit date"],
    "Address proof": ["address proof", "utility bill", "service address", "issue date"],
}


def classify(text):
    text = re.sub(r"\s+", " ", text.lower())
    scores = {kind: sum((2 if i == 0 else 1) for i, key in enumerate(keys) if key in text)
              for kind, keys in TYPES.items()}
    kind = max(scores, key=scores.get)
    return kind if scores[kind] >= 2 else "Unknown"
