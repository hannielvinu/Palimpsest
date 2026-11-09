from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

SECTIONS = ("Document Overview", "Extracted Information", "Contextual Analysis", "Visual Forensic Findings",
            "Evidence and Traceability", "Investigation Summary")


def dossier(case, result, chain):
    stream = BytesIO()
    pdf = SimpleDocTemplate(stream, title="Palimpsest | " + case["title"], author="hannielvinu",
                            leftMargin=.7*inch, rightMargin=.7*inch, topMargin=.65*inch, bottomMargin=.6*inch)
    styles = getSampleStyleSheet()
    styles["Title"].textColor = colors.HexColor("#14181F")
    styles["Title"].alignment = TA_LEFT
    styles["Heading2"].textColor = colors.HexColor("#3B4A7A")
    story = []

    def add(value, style="BodyText"):
        story.append(Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style]))

    add("Palimpsest / Investigation dossier", "Title")
    add(case["title"])
    add("All sample data is synthetic. No real personal data.")
    for index, section in enumerate(SECTIONS):
        add(section, "Heading2")
        if index == 0:
            for doc in result["documents"]:
                add(f"{doc['name']} · {doc['type']} · {doc['status']}")
                add(f"SHA-256 {doc['sha256']}")
        elif index == 1:
            for doc in result["documents"]:
                add(doc["name"], "Heading3")
                for field in doc["fields"]:
                    add(f"{field['key']} = {field['value']} · page {field['page']} · {field['method']} · unverified")
                if not doc["fields"]:
                    add("No readable fields.")
        elif index in (2, 3):
            group = [e for e in result["findings"] if (e["layer"] == "fields") == (index == 2)]
            if not group:
                add("No findings in this section.")
            for item in group:
                add(f"{item['id']} · {item['status'].replace('_', ' ')} · {item['summary']}", "Heading3")
                add("Possible benign explanation — " + item["explanation"]["harmless"])
                add("Verification — " + item["explanation"]["settle"])
        elif index == 4:
            add(f"Audit-chain head {chain['head']}")
            add(f"Case ID {case['id']}")
            for item in result["findings"]:
                add(f"{item['id']} · {item['document_id']} · page {item['page']} · region {item['bbox']} · confidence {item['confidence']:.0%}")
                add(f"{item['method']}\n{item['limits']}")
                if item["values"]:
                    add("Observed values — " + " · ".join(f"{k} = {v}" for k, v in item["values"].items()))
        else:
            summary = result["summary"]
            add(f"{summary['concern']} · {summary['score']} concern points")
            add(summary["formula"])
            add("Detector scores are heuristic. Verify observations with the issuer before making a decision.")
            decision = case["decision"]
            add(f"Human decision — {decision['action']} · {decision['timestamp']}\n{decision['reason']}" if decision else "Human decision pending.")
            add(summary["letter"])
        story.append(Spacer(1, 8))

    def footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#3B4A7A"))
        canvas.drawString(.7*inch, .34*inch, "PALIMPSEST  /  SYNTHETIC REVIEW")
        canvas.drawRightString(document.pagesize[0]-.7*inch, .34*inch, str(document.page))

    pdf.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
