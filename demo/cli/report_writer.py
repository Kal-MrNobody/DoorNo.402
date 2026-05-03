"""Report writer — saves research results + Gemini synthesis."""

import os
from datetime import datetime


REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports")


def _ensure_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def generate_filename(mode: str) -> str:
    _ensure_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = f"_{mode}" if mode != "unprotected" else ""
    return os.path.join(REPORTS_DIR, f"research{tag}_{ts}.txt")


def write_report(
    path: str,
    topic: str,
    mode: str,
    results: list[dict],
    synthesis: str,
) -> None:
    """Write a full research report to disk."""
    _ensure_dir()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sources = [r for r in results if r.get("content")]
    payments = [r for r in results if r.get("paid")]

    lines = [
        "DoorNo.402 Research Report",
        "=" * 40,
        f"Topic:    {topic}",
        f"Date:     {ts}",
        f"Mode:     {mode}",
        f"Sources:  {len(sources)}",
        "",
        "SOURCES",
        "-" * 40,
    ]

    for r in results:
        status = "blocked" if r.get("blocked") else (
            "paid" if r.get("paid") else "free")
        lines.append(
            f"  {r['domain']:20s}  {r.get('article','?'):40s}  {status}")

    lines += ["", "SYNTHESIS", "-" * 40, synthesis, ""]
    lines += ["", "PAYMENT LOG", "-" * 40]

    for r in results:
        if r.get("paid"):
            lines.append(
                f"  {r['domain']:20s}  ${r['amount']:.2f}  {r.get('tx','')}")
        elif r.get("blocked"):
            lines.append(
                f"  {r['domain']:20s}  blocked  saved ${r.get('amount',0):.2f}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


async def gemini_synthesize(topic: str, contents: list[dict]) -> str:
    """Use Gemini to synthesize collected article content."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return "synthesis unavailable — GEMINI_API_KEY not set"
    if not contents:
        return "no content collected — all payments were blocked"

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        sources_text = "\n\n".join(
            f"[{c['domain']}] {c.get('article','')}\n{c.get('content','')}"
            for c in contents if c.get("content")
        )

        resp = model.generate_content([
            {"role": "user", "parts": [{
                "text": (
                    f"You are a research analyst. Synthesize the following "
                    f"article content into a coherent analysis on the topic "
                    f"'{topic}'. Be factual, cite which source said what, "
                    f"keep it under 500 words.\n\n{sources_text}"
                )
            }]}
        ])
        return resp.text.strip()
    except Exception as e:
        return f"synthesis unavailable — {e}"
