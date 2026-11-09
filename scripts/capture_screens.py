import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def sample(page, label, concern):
    page.get_by_role("button", name=f"Load {label} case").click()
    expect(page.locator(".case-header .chip")).to_have_text(concern, timeout=40_000)
    expect(page.locator(".paper img").first).to_be_visible(timeout=20_000)
    expect(page.locator(".paper img").first).to_have_js_property("complete", True, timeout=20_000)
    assert page.locator(".paper img").first.evaluate("(image) => image.naturalWidth > 0")


def capture(page, out):
    out.mkdir(parents=True, exist_ok=True)

    def shot(name, selector=None):
        page.evaluate("document.fonts.ready")
        target = page.locator(selector) if selector else page
        target.screenshot(path=out/f"{name}.png", animations="disabled")

    shot("desk")
    sample(page,"Meena","✓ LOW")
    page.get_by_text("Name is a likely benign variant.").first.wait_for()
    card = page.locator(".finding").filter(has_text="Name is a likely benign variant.")
    card.get_by_role("button", name="Harmless explanations").click()
    expect(card).to_contain_text("Initials, shortened names and honorifics are common.")
    shot("meena")
    page.get_by_role("button",name="Case desk",exact=True).click()

    sample(page,"Ravi","◆ HIGH")
    for text in ["different text", "typography", "deductions", "bank salary credit", "pixel-near-identical"]:
        expect(page.locator(".finding h3").filter(has_text=text)).to_have_count(1)
    card = page.locator(".finding").filter(has_text="Amount typography")
    card.get_by_role("button",name="Show on document").click()
    expect(page.locator(".box.focus")).to_be_visible()
    shot("ravi")
    shot("ravi-region", ".viewer")
    page.get_by_role("button",name="Peel layer").click()
    expect(page.locator(".revision-values")).to_contain_text("48,000")
    expect(page.locator(".revision-values")).to_contain_text("88,000")
    expect(page.locator(".paper img")).to_have_count(2)
    for image in page.locator(".paper img").all():
        expect(image).to_have_js_property("complete", True, timeout=20_000)
        assert image.evaluate("(image) => image.naturalWidth > 0")
    shot("peel")
    shot("peel-panel", ".viewer")

    salary = page.locator(".finding").filter(has_text="Net pay conflicts")
    salary.get_by_role("button",name="Harmless explanations").click()
    expect(salary).to_contain_text("A bonus, arrears, split credits")
    salary.get_by_role("button",name="Related fields").click()
    salary.get_by_role("button",name="Salary credit · INR 48,000").click()
    expect(page.locator(".viewer h2")).to_have_text("Bank statement")
    page.get_by_role("button",name="Cross-document",exact=True).click()
    expect(page.locator(".mismatch")).to_have_count(2)
    shot("crossmatrix")
    page.get_by_role("button",name="Decision",exact=True).click()
    expect(page.get_by_role("button",name="Escalate")).to_be_disabled()
    page.get_by_label("Reviewer note").fill("Please confirm the payroll correction and matching bank credit.")
    page.get_by_role("button",name="Request more documents",exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Audit entry recorded")
    shot("decision")
    page.get_by_role("button",name="Dossier",exact=True).click()
    with page.expect_download() as action:
        page.get_by_role("link",name="Download PDF").click()
    assert action.value.path().read_bytes().startswith(b"%PDF-")
    page.get_by_role("button",name="Audit trail",exact=True).click()
    page.get_by_role("button",name="Verify chain").click()
    expect(page.get_by_role("status")).to_contain_text("Verified")
    shot("audit")

    page.get_by_role("button",name="Case desk",exact=True).click()
    sample(page,"injection","▲ MODERATE")
    expect(page.locator(".finding h3")).to_contain_text("Embedded text attempting")
    page.get_by_role("button",name="Dossier",exact=True).click()
    expect(page.get_by_text("Human decision pending.")).to_be_visible()
    page.get_by_role("button",name="Investigation",exact=True).click()
    shot("injection")
    page.get_by_role("button",name="Case desk",exact=True).click()
    sample(page,"degraded","? CANNOT DETERMINE")
    expect(page.locator(".finding h3")).to_contain_text("Too few readable words")
    shot("degraded")

    page.get_by_role("button",name="Benchmark",exact=True).click()
    expect(page.get_by_role("heading",name="Expected detector hits")).to_be_visible()
    shot("benchmark")
    page.get_by_role("button",name="About",exact=True).click()
    expect(page.get_by_text("no formal compliance claimed",exact=False)).to_be_visible()
    page.get_by_role("button",name="Toggle dark mode").click()
    expect(page.locator(".app")).to_have_class("app dark")
    page.set_viewport_size({"width":390,"height":844})
    page.get_by_role("button",name="Case desk",exact=True).click()
    assert page.evaluate("document.documentElement.scrollWidth") <= 391


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:7860")
    parser.add_argument("--out", type=Path, default=ROOT/"docs"/"images")
    args = parser.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width":1440,"height":900}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type=="error" else None)
        response = page.goto(args.url, wait_until="networkidle")
        assert response and response.ok
        capture(page,args.out)
        assert not errors, errors
        print("Browser verified: four sample flows, focused evidence, PDF revisions, cross-matrix, reviewer decision, download, audit, benchmark, dark theme and mobile width.")
        browser.close()


if __name__ == "__main__":
    main()
