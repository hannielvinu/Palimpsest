OPTIONS = {
    "name_variant": ("Initials, shortened names and honorifics are common.", "Confirm the full name on an issuer-verified identity document."),
    "pay_cycle": ("Bank holidays, weekends and settlement delays shift credit dates.", "Confirm the payroll cycle and matching bank credit reference."),
    "arithmetic": ("Reimbursements or a payroll correction may be listed separately.", "Provide the complete issuer payslip with the payroll adjustment breakdown."),
    "salary_credit": ("A bonus, arrears, split credits or a different pay cycle can explain the difference.", "Provide the statement covering the full pay cycle and the payroll credit reference."),
    "font_baseline": ("A template can use mixed fonts or render amounts differently.", "Provide the original digital document from the issuer."),
    "layer_peel": ("The issuer may have corrected an earlier version before distribution.", "Provide the issuer’s final copy and any correction notice."),
    "signature_reuse": ("A legitimate workflow may apply the same approved signature stamp.", "Confirm the issuer’s signature-stamp policy and obtain an issuer-verified copy."),
    "hidden_text": ("An exported template or accessibility layer can retain draft instructions.", "Provide a clean issuer export and confirm the document workflow."),
    "quality": ("A phone scan may be blurred or low resolution.", "Provide a sharper scan or an original PDF."),
    "ela": ("JPEG edges and ordinary resaving produce uneven compression errors.", "Provide the earliest available image or direct issuer export."),
    "copy_move": ("Logos, ruled layouts and repeated graphics can generate similar patches.", "Compare with a blank template and an issuer copy."),
}


def explain(item):
    harmless, settle = OPTIONS.get(item["detector"], ("A template difference or extraction error may explain this.",
                                                      "Verify the value on a clearer copy from the issuer."))
    return {"why": item["summary"], "harmless": harmless, "settle": settle}
