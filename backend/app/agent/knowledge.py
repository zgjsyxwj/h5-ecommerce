from pathlib import Path

FAQ_MARKDOWN = (Path(__file__).parent / "faq.md").read_text(encoding="utf-8")
