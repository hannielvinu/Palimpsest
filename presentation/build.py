"""Build the eight-slide submission deck from real local captures."""
import argparse
from io import BytesIO
import json
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt
import qrcode

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT/"docs"/"images"
RESULTS = ROOT/"data"/"benchmark"/"results"
REPO = "https://github.com/hannielvinu/Palimpsest"

W, H = 13.333333, 7.5
PARCHMENT, PAPER, INK = "F6F1E7", "FFFDF8", "14181F"
NAVY, SLATE, MUTED = "19212D", "2B3340", "4F5661"
RULE, GOLD, OX, SAGE, INDIGO = "E3DACA", "DFC896", "8C2F39", "2D6748", "3B4A7A"
SERIF, SANS, MONO = "Fraunces", "Inter", "JetBrains Mono"


def color(hex_value):
    return RGBColor.from_string(hex_value)


def text(slide, value, x, y, w, h, *, font=SANS, size=17, ink=INK, bold=False, align=None, url=None):
    shape = slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    frame = shape.text_frame
    frame.clear()
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.TOP
    for i, line in enumerate(value.split("\n")):
        p = frame.paragraphs[0] if i==0 else frame.add_paragraph()
        p.space_after = Pt(0)
        p.line_spacing = 1.06
        if align is not None:
            p.alignment = align
        r = p.add_run()
        r.text = line
        r.font.name = font
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color(ink)
    if url:
        shape.click_action.hyperlink.address = url
    return shape


def rect(slide, x, y, w, h, fill, stroke=None, angle=0):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color(fill)
    if stroke:
        shape.line.color.rgb = color(stroke)
        shape.line.width = Pt(.8)
    else:
        shape.line.fill.background()
    shape.rotation = angle
    return shape


def shot(slide, file, x, y, w, h, *, crop=None, desc):
    with Image.open(IMAGES/file) as original:
        im = original.crop(crop) if crop else original.copy()
    ratio = min(w/im.width,h/im.height)
    iw, ih = im.width*ratio, im.height*ratio
    stream = BytesIO()
    im.save(stream,"PNG")
    stream.seek(0)
    image = slide.shapes.add_picture(stream,Inches(x+(w-iw)/2),Inches(y+(h-ih)/2),Inches(iw),Inches(ih))
    image._element.nvPicPr.cNvPr.set("descr",desc)
    return image


def foot(slide, n, source, dark=False):
    rect(slide,.64,7.01,12.05,.012,"516075" if dark else RULE)
    text(slide,source,.65,7.12,10.95,.22,font=MONO,size=8.2,ink=GOLD if dark else MUTED)
    text(slide,f"{n:02d} / 08",11.75,7.11,.93,.24,font=MONO,size=9,ink=GOLD if dark else MUTED,align=PP_ALIGN.RIGHT)


def slide(deck,n,section,title,source, notes, dark=False):
    s = deck.slides.add_slide(deck.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = color(NAVY if dark else PARCHMENT)
    text(s,section,.65,.36,12,.23,font=MONO,size=10.5,ink=GOLD if dark else INDIGO)
    if title:
        text(s,title,.63,.77,12.05,.75,font=SERIF,size=40,ink=PAPER if dark else INK,bold=True)
    foot(s,n,source,dark)
    s.notes_slide.notes_text_frame.text = notes
    return s


def build(live_url):
    benchmark = json.loads((RESULTS/"benchmark.json").read_text(encoding="utf8"))
    robustness = json.loads((RESULTS/"robustness.json").read_text(encoding="utf8"))["conditions"]
    rotation = next(row for row in robustness if row["condition"]=="rotation")
    deck = Presentation()
    deck.slide_width,deck.slide_height = Inches(W),Inches(H)
    deck.core_properties.title = "Palimpsest"
    deck.core_properties.subject = "DataOps Innovation Hackathon 2026"
    deck.core_properties.author = "hannielvinu"
    deck.core_properties.keywords = "document forensics, evidence, human review"

    s = slide(deck,1,"DATAOPS INNOVATION HACKATHON 2026   /   HACK THE CORE",None,
              "PROBLEM STATEMENT 1  ·  AI-POWERED DOCUMENT FORENSICS AND CONTEXTUAL INTELLIGENCE",
              "0:00–0:18. Introduce Palimpsest and the manuscript metaphor. Explain that traces in documents can lead to verification questions a reviewer can act on.",True)
    text(s,"Palimpsest",.62,1.55,7.55,1.44,font=SERIF,size=74,ink=PAPER,bold=True)
    text(s,"Every document has a second layer.",.68,3.08,7.35,.49,font=SERIF,size=27,ink=GOLD)
    text(s,"A palimpsest is a manuscript scraped clean and rewritten. Traces of the earlier writing remain.",.7,4.02,6.55,1.08,size=20,ink="E4E9F2")
    text(s,"BUILT BY HANNIELVINU",.71,5.78,7,.35,font=MONO,size=12,ink=GOLD)
    rect(s,9.14,1.56,2.77,3.68,"A69778",GOLD,14)
    rect(s,8.76,1.48,2.79,3.69,PAPER,"C5AE85",-9)
    text(s,"FIELD NOTE",9.02,2.01,2.1,.28,font=MONO,size=10,ink=INDIGO)
    text(s,"Case\nevidence",8.97,2.55,2.4,1.48,font=SERIF,size=34,ink=NAVY,bold=True)
    rect(s,9.05,4.05,1.90,.018,"B0A58E")
    rect(s,9.05,4.32,1.45,.018,"B0A58E")
    rect(s,9.05,4.58,1.68,.018,"B0A58E")

    s = slide(deck,2,"THE TWO APPLICANTS","Meena and Ravi",
              "SOURCE  ·  MEENA AND RAVI SAMPLE CASES, CAPTURED FROM THE RUNNING LOCAL APP",
              "0:18–0:42. Meena's scan is blurry and her bank uses an initial. The credit fits the pay cycle. Ravi's payslip contains a changed value and invites independent checks. Both applicants are fictional.")
    for x, name, accent, status, description, file, crop in [
        (.64,"Meena",SAGE,"LOW CONCERN","A blurry scan, an initial and a normal payroll delay.","meena.png",(48,112,1391,306)),
        (6.78,"Ravi",OX,"HIGH CONCERN","A payslip amount that conflicts with the credit and an earlier PDF revision.","ravi.png",(48,100,1391,285)),
    ]:
        rect(s,x,1.86,5.91,4.54,PAPER,RULE)
        rect(s,x,1.86,5.91,.055,accent)
        text(s,status,x+.24,2.15,5.44,.25,font=MONO,size=11,ink=accent,bold=True)
        text(s,name,x+.23,2.55,5.44,.67,font=SERIF,size=36,bold=True)
        text(s,description,x+.24,3.38,5.35,1.05,size=20)
        shot(s,file,x+.17,4.72,5.57,1.21,crop=crop,desc=f"{name}'s case title and concern label in Palimpsest")
    text(s,"All sample data is synthetic. No real personal data.",.65,6.63,12,.25,size=12,ink=MUTED)

    s = slide(deck,3,"THE GAP","Reading and verifying a payslip",
              "SOURCE  ·  RAVI SAMPLE CASE AND CAPTURED PAYROLL REGIONS",
              "0:42–0:59. OCR can read a number. Verification asks how the number relates to neighboring fields, the bank record and earlier PDF revisions. Those checks generate questions and preserve the source.")
    text(s,"OCR reads a value.",.67,1.87,6.04,.72,font=SERIF,size=36,bold=True)
    text(s,"A reviewer needs to know what corroborates it.",.68,2.74,6.02,1.36,font=SERIF,size=29,ink=OX)
    text(s,"Compare the payroll arithmetic, the bank credit and the document’s own history.",.7,4.34,5.81,1.16,size=20,ink=MUTED)
    rect(s,7.02,1.86,5.64,4.49,PAPER,RULE)
    text(s,"OBSERVED ON THE PAYSLIP",7.26,2.12,5.15,.31,font=MONO,size=11,ink=INDIGO)
    shot(s,"ravi.png",7.23,2.57,5.18,2.45,crop=(327,750,929,898),desc="Gross pay, deductions and red-boxed net pay on Ravi's payslip")
    text(s,"Which source supports this amount?",7.28,5.27,5.10,.6,font=SERIF,size=20,ink=OX)

    s = slide(deck,4,"SYSTEM DESIGN","From originals to evidence",
              "SOURCE  ·  BACKEND PIPELINE AND API STATUS STEPS",
              "0:59–1:21. Follow the top row through document ingestion, extraction and visual inspection. The bottom row checks relationships, matches documents, and links evidence and explanations to a dossier. Human review follows the pipeline.")
    steps = [
        ("Ingest","SHA-256 and file limits"),("Classify","Keywords and layout rows"),("Extract","PDF text or Tesseract"),
        ("Visual forensics","Typography, signatures, history"),("Context","Arithmetic and field rules"),
        ("Cross-document","Identity and payroll window"),("Evidence","Source boxes and alternatives"),("Dossier","Case file and audit head"),
    ]
    for i,(name,detail) in enumerate(steps):
        row,col=divmod(i,4)
        x,y=.65+col*3.08,1.89+row*1.61
        rect(s,x,y,2.82,1.37,PAPER,RULE)
        text(s,f"{i+1:02d}",x+.15,y+.12,2.45,.21,font=MONO,size=10,ink=INDIGO)
        text(s,name,x+.15,y+.42,2.51,.34,font=SERIF,size=16,bold=True)
        text(s,detail,x+.15,y+.87,2.50,.35,size=11.6,ink=MUTED)
        if col<3:
            text(s,"→",x+2.86,y+.43,.2,.35,size=15,ink=INDIGO)
    rect(s,.65,5.45,12.05,.76,NAVY)
    text(s,"HUMAN REVIEW",.9,5.69,2.62,.28,font=MONO,size=11,ink=GOLD)
    text(s,"Clear, request more documents, or escalate with a reason.",3.46,5.65,8.86,.41,size=16,ink=PAPER)

    s = slide(deck,5,"VISUAL EVIDENCE","Peel the Layer",
              "SOURCE  ·  RAVI’S SYNTHETIC PAYSLIP AND RETAINED PDF REVISION, LOCAL CAPTURE",
              "1:21–1:51. Click the typography finding to see the red box on current net pay. Show the earlier INR 48,000 and current INR 88,000 side by side. This works because the PDF retained its earlier bytes. A legitimate correction can also leave incremental history.")
    text(s,"CURRENT AMOUNT",.67,1.80,5.1,.23,font=MONO,size=11,ink=INDIGO)
    text(s,"INR 88,000",.65,2.12,5.08,.76,font=SERIF,size=39,ink=OX,bold=True)
    rect(s,.65,3.08,5.12,1.53,PAPER,RULE)
    shot(s,"ravi.png",.77,3.12,4.88,1.44,crop=(329,755,933,898),desc="Red box around the INR 88,000 net pay region")
    text(s,"Prior net pay recovered",.67,4.94,5.11,.38,font=SERIF,size=20,bold=True)
    text(s,"INR 48,000 · The earlier bytes survived an incremental save.",.67,5.49,5.09,.74,size=17,ink=MUTED)
    shot(s,"peel-panel.png",6.04,1.55,6.63,5.30,desc="Prior and current salary slip pages with the two net pay values side by side")

    s = slide(deck,6,"CONTEXT AND HUMAN REVIEW","The bank credit and the next step",
              "SOURCE  ·  RAVI CASE MATRIX, REVIEWER DECISION AND APPLICANT LETTER, LOCAL CAPTURES",
              "1:51–2:18. The bank credit is INR 48,000, matching gross minus deductions. A bonus, arrears, split credit or payroll correction might explain the difference. Ask for the final issuer record and matching credit reference. Show the recorded reviewer action.")
    rect(s,.66,1.84,5.74,4.91,PAPER,RULE)
    text(s,"PAY-CYCLE CONFLICT",.9,2.1,5.27,.25,font=MONO,size=11,ink=OX)
    text(s,"The bank credit matches the prior amount.",.88,2.59,5.22,1.03,font=SERIF,size=25,bold=True)
    text(s,"Payslip INR 88,000 · Bank INR 48,000",.9,3.77,5.16,.33,size=14.8,ink=OX,bold=True)
    shot(s,"crossmatrix.png",.87,4.15,5.26,.73,crop=(78,572,1354,660),desc="Cross-document table showing net pay and bank salary credit mismatch")
    text(s,"A bonus, split credit or correction could explain the difference.",.9,4.98,5.16,.95,size=16,ink=MUTED)
    text(s,"Request more documents",.9,6.04,5.09,.32,size=14,bold=True,ink=INDIGO)
    shot(s,"decision.png",6.55,1.81,6.1,4.91,crop=(50,190,1392,865),desc="Concern breakdown, applicant letter and recorded reviewer decision")

    s = slide(deck,7,"SYNTHETIC EVALUATION","Measured results and limits",
              "SOURCE  ·  DATA/BENCHMARK/RESULTS/BENCHMARK.JSON AND ROBUSTNESS.JSON",
              "2:18–2:43. The synthetic benchmark is self-generated. Nine of ten changed cases were flagged, with one miss, and no genuine flags among ten benchmark controls. Rotation caused one false alarm in five. The hidden instruction was flagged and had no decision authority. Briefly point to the rubric map.")
    stats = [
        (f"{benchmark['caught']} / {benchmark['caught']+benchmark['missed']}","Changed cases flagged",OX),
        (f"{benchmark['false_alarms']} / {benchmark['genuine']}","Genuine cases flagged",SAGE),
        (f"{rotation['flagged']} / {rotation['total']}","Rotated scans flagged",INDIGO),
    ]
    for i,(value,title,accent) in enumerate(stats):
        x=.65+4.09*i
        rect(s,x,1.74,3.89,1.52,PAPER,RULE)
        text(s,value,x+.17,1.9,3.54,.71,font=SERIF,size=37,ink=accent,bold=True)
        text(s,title,x+.19,2.75,3.53,.29,size=13.1,bold=True)
    text(s,"The hidden instruction surfaced as evidence. The review stayed pending.",.68,3.48,11.98,.34,size=15,bold=True)
    states=[("Implemented","Revision recovery and audit"),("Partial","Visual and text heuristics"),("Planned","Blind evaluation"),("Unsupported","Flattened history recovery")]
    for i,(state,detail) in enumerate(states):
        x=.67+(i%2)*6.12
        y=4.0+(i//2)*.49
        text(s,state,x,y,1.53,.29,size=12.4,bold=True,ink=INDIGO)
        text(s,detail,x+1.55,y,4.32,.30,size=12.4)
    rect(s,.66,5.14,12.02,.012,RULE)
    text(s,"RUBRIC COVERAGE",.67,5.35,11.97,.24,font=MONO,size=10,ink=INDIGO)
    text(s,"OCR & Information Extraction · Document Understanding · Visual Forensic Analysis · Contextual Intelligence\nEvidence & Traceability · AI Reasoning & Explainability · Technical Implementation · Innovation",
         .67,5.74,11.97,.72,size=12,ink=MUTED)
    text(s,benchmark["label"],.67,6.55,11.96,.27,size=11,ink=MUTED)

    s = slide(deck,8,"NEXT 30 DAYS","What we’ll verify next",
              "PALIMPSEST  /  BUILT BY HANNIELVINU",
              "2:43–3:00. Close on the limits. Flattened history cannot be recovered and concern weights are heuristic. The next steps are a blind set, better layout support, and stronger custody. Point to the link and thank the audience.",True)
    for i,(heading,detail) in enumerate([
        ("Blind evaluation","Add independent documents and measure by detector."),
        ("Scan and layout coverage","Improve rotation handling and broaden labeled templates."),
        ("Stronger custody","Isolate native parsers and checkpoint the audit chain."),
    ]):
        y=1.76+i*1.12
        text(s,heading,.68,y,7.08,.44,font=SERIF,size=22,ink=PAPER,bold=True)
        text(s,detail,.7,y+.48,7.05,.44,size=15.4,ink="D8E0F0")
    text(s,"Source repository",.7,5.21,7.1,.26,font=MONO,size=11,ink=GOLD)
    text(s,"github.com/hannielvinu/Palimpsest",.7,5.59,7.06,.34,size=16,ink=PAPER,url=REPO)
    text(s,live_url or "Public demo deployment pending",.7,6.17,7.1,.34,size=14,ink=GOLD,url=live_url)
    qr=qrcode.make(live_url or REPO)
    stream=BytesIO()
    qr.save(stream,format="PNG")
    stream.seek(0)
    rect(s,8.92,1.77,3.27,3.85,PAPER)
    picture=s.shapes.add_picture(stream,Inches(9.23),Inches(2.04),Inches(2.65),Inches(2.65))
    picture._element.nvPicPr.cNvPr.set("descr","QR code to " + ("the live app" if live_url else "the public repository"))
    text(s,"LIVE APP" if live_url else "PUBLIC REPOSITORY",9.04,4.91,3.04,.27,font=MONO,size=10.5,ink=INDIGO,align=PP_ALIGN.CENTER)
    text(s,"Flattened PDFs lose recoverable history.",8.88,5.98,3.4,.61,size=13,ink="D8E0F0",align=PP_ALIGN.CENTER)

    out=ROOT/"presentation"/"Palimpsest.pptx"
    deck.save(out)
    print(out)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--live-url")
    args=parser.parse_args()
    if args.live_url:
        url=urlparse(args.live_url)
        if url.scheme!="https" or not url.hostname:
            parser.error("Use the verified public HTTPS URL.")
    build(args.live_url)
