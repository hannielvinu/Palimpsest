"""Record real browser interactions and mix offline narration into a submission MP4."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from textwrap import wrap
from time import monotonic
import wave

from imageio_ffmpeg import get_ffmpeg_exe
from playwright.sync_api import expect, sync_playwright

from capture_screens import ROOT, sample

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Voice,Arial,32,&H00F8FDFF,&H00000000,&H002D2119,&H002D2119,0,0,0,0,100,100,0,0,1,0,0,2,205,205,22,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def timestamp(seconds):
    hundredths = round(seconds*100)
    hours, rest = divmod(hundredths, 360000)
    minutes, rest = divmod(rest, 6000)
    seconds, fraction = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{fraction:02d}"


def voiceover(directory):
    source = (ROOT/"docs"/"demo-script.md").read_text(encoding="utf8")
    chapters = [chunk.partition("\n")[2].strip() for chunk in re.split(r"^## \d{2} / ", source, flags=re.M)[1:]]
    narration = directory/"narration.json"
    narration.write_text(json.dumps(chapters), encoding="utf8")
    subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",
                    str(ROOT/"scripts"/"narrate_demo.ps1"),str(narration),str(directory)],check=True)
    audio = []
    for index, text in enumerate(chapters):
        with wave.open(str(directory/f"voice-{index:02d}.wav")) as stream:
            audio.append((text,stream.getparams(),stream.readframes(stream.getnframes())))
    return audio


def record(directory, url, audio):
    starts = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width":1440,"height":900}, accept_downloads=True,
                                      record_video_dir=str(directory), record_video_size={"width":1440,"height":900})
        start = monotonic()
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        page.evaluate("document.fonts.ready")

        def hold(during=None):
            index = len(starts)
            text, params, _ = audio[index]
            starts.append(monotonic()-start)
            print(f"Recording {index+1:02d} at {starts[-1]:.1f}s — {text.split('.')[0]}", flush=True)
            duration = params.nframes / params.framerate
            if during:
                page.wait_for_timeout(round(duration * .45 * 1000))
                during()
            remaining = starts[-1] + duration + .48 - (monotonic()-start)
            if remaining > 0:
                page.wait_for_timeout(round(remaining*1000))

        def button(name):
            return page.get_by_role("button", name=name, exact=True)

        def home():
            button("Case desk").click()

        def card(text):
            return page.locator(".finding").filter(has_text=text)

        hold()
        sample(page,"Meena","✓ LOW")
        card("Name is a likely benign variant.").get_by_role("button",name="Harmless explanations").click()
        hold()

        home()
        sample(page,"Ravi","◆ HIGH")
        card("Amount typography").get_by_role("button",name="Show on document").click()
        expect(page.locator(".box.focus")).to_be_visible()
        hold()

        button("◫ Peel layer").click()
        expect(page.locator(".revision-values")).to_contain_text("48,000")
        expect(page.locator(".revision-values")).to_contain_text("88,000")
        expect(page.locator(".paper img").first).to_have_js_property("complete",True,timeout=20_000)
        hold()

        button("Cross-document").click()
        expect(page.locator(".mismatch")).to_have_count(2)
        def show_signature():
            button("Investigation").click()
            card("Two signature regions").get_by_role("button",name="Show on document").click()
            page.locator(".raster").evaluate("(node) => { node.scrollTop = node.scrollHeight }")
        hold(show_signature)

        button("Decision").click()
        page.get_by_label("Reviewer note").fill("Please confirm the payroll correction and matching bank credit.")
        button("Request more documents").click()
        expect(page.get_by_role("status")).to_contain_text("Audit entry recorded")
        hold()

        button("Dossier").click()
        def verify_dossier():
            with page.expect_download() as download:
                page.get_by_role("link",name="Download PDF").click()
            assert download.value.path().read_bytes().startswith(b"%PDF-")
            button("Audit trail").click()
            button("Verify chain").click()
            expect(page.get_by_role("status")).to_contain_text("Verified")
        hold(verify_dossier)

        home()
        sample(page,"injection","▲ MODERATE")
        page.get_by_text("Method, values and limits",exact=True).click()
        expect(page.get_by_text("ignore previous instructions",exact=False)).to_be_visible()
        hold()

        home()
        sample(page,"degraded","? CANNOT DETERMINE")
        expect(page.locator(".finding h3")).to_contain_text("Too few readable words")
        hold()

        button("Benchmark").click()
        expect(page.get_by_role("heading",name="Expected detector hits")).to_be_visible()
        hold()

        home()
        hold()
        context.close()
        raw = Path(page.video.path())
        browser.close()
    assert len(starts)==len(audio)
    return raw,starts


def mix(directory, starts, audio):
    params = audio[0][1]
    frame_bytes = params.nchannels * params.sampwidth
    lines = []
    cursor = 0
    with wave.open(str(directory/"narration.wav"),"wb") as combined:
        combined.setparams(params)
        for start, (text, info, payload) in zip(starts,audio):
            assert info[:3] == params[:3]
            position = round(start*params.framerate)
            combined.writeframesraw(bytes(max(0,position-cursor)*frame_bytes))
            combined.writeframesraw(payload)
            cursor = position + info.nframes
            duration = info.nframes / info.framerate
            pieces = wrap(text, width=150, break_long_words=False, break_on_hyphens=False)
            words = sum(len(piece.split()) for piece in pieces)
            running = start
            for piece in pieces:
                end = running + duration*len(piece.split())/words
                lines.append(f"Dialogue: 0,{timestamp(running)},{timestamp(end)},Voice,,0,0,0,,{piece}")
                running = end
    (directory/"captions.ass").write_text(ASS_HEADER+"\n".join(lines)+"\n", encoding="utf8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url",default="http://127.0.0.1:7860")
    parser.add_argument("--output",type=Path,default=ROOT/"demo"/"Palimpsest-demo.mp4")
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory() as tmp:
        directory = Path(tmp)
        audio = voiceover(directory)
        raw, starts = record(directory,args.url,audio)
        mix(directory,starts,audio)
        candidate = directory/"Palimpsest-demo.mp4"
        trim = f"{max(0, starts[0]-.5):.3f}"
        subprocess.run([get_ffmpeg_exe(),"-hide_banner","-loglevel","warning","-y","-ss",trim,"-i",str(raw),"-ss",trim,"-i","narration.wav",
                        "-vf",f"scale=1536:960:flags=lanczos,pad=1920:1080:192:0:0x19212d,setpts=PTS+{trim}/TB,ass=captions.ass,setpts=PTS-STARTPTS",
                        "-af","loudnorm=I=-16:TP=-1.5:LRA=11","-c:v","libx264","-preset","fast","-crf","19",
                        "-pix_fmt","yuv420p","-c:a","aac","-ar","48000","-b:a","128k","-movflags","+faststart",str(candidate)],
                       cwd=directory,check=True)
        output.write_bytes(candidate.read_bytes())
    print(output)


if __name__=="__main__":
    main()
