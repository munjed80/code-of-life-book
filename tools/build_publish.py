#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداةُ بناء نسخة النشر النظيفة (publish/).

تُنتج هذه الأداة ثلاث صيغ نهائيّةٍ من الكتاب، خاليةٍ من الملاحظات التحريريّة
وعلامات الحواشي الخام والإشارات إلى ملفات المشروع الداخليّة:

1) publish/book-final.md       — نسخة نظيفة بصيغة ماركداون.
2) publish/book-final-print.txt — نصّ نظيف للطباعة.
3) publish/book-final-ebook.html — نسخة إلكترونيّة RTL بصفحة عنوان وفهرس.

الاستعمال:
    python3 tools/build_publish.py
"""

from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent
CHAPTERS_DIR = ROOT / "chapters"
PUBLISH_DIR = ROOT / "publish"

BOOK_TITLE = "كود الحياة"
BOOK_SUBTITLE = "من النظام إلى الخالق، ومن الخالق إلى معنى الإنسان وفعله"
AUTHOR = "منجد محمد السيد"

FILES_ORDER: List[Tuple[str, str]] = [
    ("introduction.md", "المقدمة"),
    ("chapter-01.md", "الفصل الأول"),
    ("chapter-02.md", "الفصل الثاني"),
    ("chapter-03.md", "الفصل الثالث"),
    ("chapter-04.md", "الفصل الرابع"),
    ("chapter-05.md", "الفصل الخامس"),
    ("chapter-06.md", "الفصل السادس"),
    ("chapter-07.md", "الفصل السابع"),
    ("chapter-08.md", "الفصل الثامن"),
    ("chapter-09.md", "الفصل التاسع"),
    ("chapter-10.md", "الفصل العاشر"),
    ("chapter-11.md", "الفصل الحادي عشر"),
    ("chapter-12.md", "الفصل الثاني عشر"),
    ("appendix-a-formative-bridge.md", "الملحق أ"),
    ("conclusion.md", "خاتمة الكتاب"),
]

# أسماء الملفات الداخليّة التي يَجب ألا تَظهر في نسخة النشر
INTERNAL_FILES_PATTERN = (
    r"(?:BOOK_RULES|GLOSSARY|SCIENCE_NOTES|QURAN_EVIDENCE|"
    r"MATURE_THESIS|CRITIQUE|IBN_TAYMIYYAH_NOTES|CONCEPT_SEEDS|"
    r"DEEP_THINKING_NOTES|OUTLINE|README)\.md"
)

# عنوان قسم الملاحظات التحريريّة (يُحذف هو وما بعده في كل فصل)
EDITORIAL_HEADING_RE = re.compile(
    r"^\s*#{1,6}\s*(?:ملاحظات\s+تحريريّة|قائمة\s+الأدلة\s+في\s+هذا\s+الفصل)"
    r"[^\n]*$",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# تنظيف نصّ المصدر قبل التحليل
# ---------------------------------------------------------------------------

def strip_editorial_section(md: str) -> str:
    """يَحذف قسم 'ملاحظات تحريريّة للمراجعة' وما بعده من الفصل."""
    m = EDITORIAL_HEADING_RE.search(md)
    if m:
        md = md[: m.start()].rstrip() + "\n"
    return md


def remove_internal_references(text: str) -> str:
    """يَحذف من النصّ كلَّ ما يُحيل إلى ملفات المشروع الداخليّة."""
    fn = INTERNAL_FILES_PATTERN

    # 0) إصلاحاتٌ نَصّيّةٌ مُسبقة لصياغاتٍ يُؤدّي حذفُ اسم الملفّ منها إلى
    #    جُملةٍ مَبتورة، فنُعيد صياغتَها قبل التنظيف العامّ.
    text = re.sub(
        r"يَلتزم\s+بِما\s+نَصّت\s+عليه\s+`?" + fn + r"`?\s*\([^()\n]*\)",
        "يَلتزم بقاعدةٍ من قواعد الكتاب",
        text,
    )

    # 1) أزواج أقواسٍ تَحوي اسم ملفٍ داخليّ
    text = re.sub(r"\s*\([^()\n]*?" + fn + r"[^()\n]*?\)", "", text)

    # 2) جُملةٌ بين شَرطتَين تَحوي اسمَ ملفٍ داخليّ
    text = re.sub(
        r"\s*[—–\-]\s*[^—–\n]*?" + fn + r"[^—–\n]*?[—–\-]\s*",
        " ",
        text,
    )

    # 3) صيغةٌ شائعة: "التزامًا بـ`XX.md`" أو "في `XX.md`، الباب N"
    rule_words = (
        r"(?:الباب|القاعدة|القواعد|الملحق|الفصل|الجزء|الفقرة|باب|قاعدة|الصفحة)"
    )
    file_then_tail = (
        r"(?:التزامًا\s+بـ?|في|بـ|على|عليه)\s*`?" + fn + r"`?"
        r"(?:\s*،\s*" + rule_words + r"[^،.\n:؛()—–]*)*"
        r"(?:\s*\([^()\n]*?" + rule_words + r"[^()\n]*?\))?"
    )
    text = re.sub(file_then_tail, "", text)

    # 4) أيّ ذكرٍ متبقٍّ لاسم ملفٍ داخليّ بمفرده
    text = re.sub(r"`?" + fn + r"`?", "", text)

    # 5) أقواسٌ بقايا تَحوي إحالةً إلى قاعدةٍ من قواعد الكتاب فقط — تُحذف
    #    لأنّها لم تَعد ذاتَ معنًى للقارئ بعد إزالة المراجع الداخليّة.
    bracket_only_rule = (
        r"\s*\(\s*" + rule_words + r"\s+[\d٠-٩]+[^()\n]{0,80}?\)"
    )
    text = re.sub(bracket_only_rule, "", text)

    return text


def remove_editorial_phrases(text: str) -> str:
    """يَحذف عباراتٍ تحريريّةً داخليّةً من المتن."""
    # «حالة التوثيق: ...» إلى نهاية الجملة
    text = re.sub(
        r"\s*\*{0,2}حالة\s+التوثيق\*{0,2}\s*:?[^\.\n]*\.",
        "",
        text,
    )
    # أقواسٌ تَحوي «يحتاج إلى توثيق» أو نحوَه
    text = re.sub(
        r"\s*\([^()\n]*?(?:يحتاج\s+إلى\s+توثيق|يَحتاج\s+إلى\s+توثيق|"
        r"يُحال\s+في\s+النسخة\s+النهائيّة|يُؤجَّل\s+إلى\s+الذيل\s+التحريري)"
        r"[^()\n]*?\)",
        "",
        text,
    )
    return text


def remove_footnote_markers(text: str) -> str:
    """يَحذف علاماتِ الحواشي الخام مثل [^causality] وتعريفاتِها."""
    # تعريفاتُ الحواشي في بداية الأسطر: [^xxx]: ...
    text = re.sub(
        r"^\s*\[\^[A-Za-z0-9_-]+\]:[^\n]*(?:\n[ \t]+[^\n]*)*\n?",
        "",
        text,
        flags=re.MULTILINE,
    )
    # علاماتُ الحواشي داخل المتن
    text = re.sub(r"\[\^[A-Za-z0-9_-]+\]", "", text)
    return text


def cleanup_whitespace_and_punct(text: str) -> str:
    """يُنظّف الفراغاتِ والترقيمَ بعد عمليّات الحذف."""
    # دمج المسافات المتعدّدة
    text = re.sub(r"[ \t]{2,}", " ", text)
    # إزالة فاصلة عربيّة أو لاتينيّة قبل علامة ترقيم نهايةٍ
    text = re.sub(r"\s*،\s*([\.:؛])", r"\1", text)
    # إزالة فاصلتَين عربيّتَين متتاليتَين
    text = re.sub(r"،\s*،", "،", text)
    # مسافة قبل فاصلة
    text = re.sub(r"\s+،", "،", text)
    # مسافة قبل نقطة
    text = re.sub(r"\s+\.", ".", text)
    # شَرطتان متتاليتان
    text = re.sub(r"[—–]\s*[—–]", "—", text)
    # أقواس فارغة
    text = re.sub(r"\(\s*\)", "", text)
    # أقواس عربيّة قَبل/بعد علامات ترقيم
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\(\s+", "(", text)
    # إزالة أسطر فارغة زائدة
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def clean_chapter_source(md: str) -> str:
    """يُجري كلَّ مراحل التنظيف على نصّ فصلٍ خام."""
    md = strip_editorial_section(md)
    md = remove_footnote_markers(md)
    md = remove_internal_references(md)
    md = remove_editorial_phrases(md)
    md = cleanup_whitespace_and_punct(md)
    return md


# ---------------------------------------------------------------------------
# مُحلِّل ماركداون مبسَّط (مأخوذ من tools/build_print.py مع تَعديل طفيف)
# ---------------------------------------------------------------------------

def parse_blocks(md: str) -> List[dict]:
    blocks: List[dict] = []
    lines = md.splitlines()
    i = 0
    para_buf: List[str] = []

    def flush_para():
        if para_buf:
            text = " ".join(s.strip() for s in para_buf).strip()
            if text:
                blocks.append({"type": "para", "text": text})
            para_buf.clear()

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if stripped == "":
            flush_para()
            i += 1
            continue

        if re.fullmatch(r"-{3,}|_{3,}|\*{3,}", stripped):
            flush_para()
            blocks.append({"type": "hr"})
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            blocks.append({
                "type": "heading",
                "level": len(m.group(1)),
                "text": m.group(2).strip(),
            })
            i += 1
            continue

        if stripped.startswith(">"):
            flush_para()
            quote_lines = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                q = re.sub(r"^\s*>\s?", "", lines[i])
                quote_lines.append(q.strip())
                i += 1
            text = " ".join(s for s in quote_lines if s).strip()
            blocks.append({"type": "blockquote", "text": text})
            continue

        m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m:
            flush_para()
            blocks.append({
                "type": "list_item",
                "ordered": True,
                "number": int(m.group(1)),
                "text": m.group(2).strip(),
            })
            i += 1
            continue

        m = re.match(r"^[-*+]\s+(.*)$", stripped)
        if m:
            flush_para()
            blocks.append({
                "type": "list_item",
                "ordered": False,
                "text": m.group(1).strip(),
            })
            i += 1
            continue

        para_buf.append(stripped)
        i += 1

    flush_para()
    return blocks


def clean_inline(text: str) -> str:
    if not text:
        return text
    s = text
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    for _ in range(3):
        s = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", s)
        s = re.sub(r"___(.+?)___", r"\1", s)
        s = re.sub(r"__(.+?)__", r"\1", s)
        s = re.sub(r"(?<!_)_(?!_)([^_]+?)(?<!_)_(?!_)", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = s.replace("_", "").replace("*", "").replace("`", "")
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s


def to_arabic_numerals(n: int) -> str:
    return str(n).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


# ---------------------------------------------------------------------------
# توليد ماركداون نظيف (publish/book-final.md)
# ---------------------------------------------------------------------------

def build_clean_markdown(file_blocks: List[Tuple[str, List[dict]]]) -> str:
    out: List[str] = []
    out.append(f"# {BOOK_TITLE}")
    out.append("")
    out.append(f"## {BOOK_SUBTITLE}")
    out.append("")
    out.append(f"تأليف: {AUTHOR}")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## فهرس الكتاب")
    out.append("")
    for _, label in FILES_ORDER:
        out.append(f"- {label}")
    out.append("")
    out.append("---")
    out.append("")

    for fname, _label in FILES_ORDER:
        blocks = dict(file_blocks).get(fname)
        if blocks is None:
            continue
        for b in blocks:
            t = b["type"]
            if t == "heading":
                level = min(max(b["level"], 1), 6)
                txt = b["text"].strip()
                if not txt:
                    continue
                out.append(f"{'#' * level} {txt}")
                out.append("")
            elif t == "para":
                out.append(b["text"].strip())
                out.append("")
            elif t == "blockquote":
                out.append(f"> {b['text'].strip()}")
                out.append("")
            elif t == "hr":
                out.append("---")
                out.append("")
            elif t == "list_item":
                if b.get("ordered"):
                    out.append(f"{b['number']}. {b['text'].strip()}")
                else:
                    out.append(f"- {b['text'].strip()}")
        out.append("")

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


# ---------------------------------------------------------------------------
# توليد نصّ الطباعة (publish/book-final-print.txt)
# ---------------------------------------------------------------------------

def build_print_text(file_blocks: List[Tuple[str, List[dict]]]) -> str:
    out: List[str] = []
    out.append(BOOK_TITLE)
    out.append("")
    out.append(BOOK_SUBTITLE)
    out.append("")
    out.append(f"تأليف: {AUTHOR}")
    out.append("")
    out.append("")
    out.append("فهرس الكتاب")
    out.append("")
    for _, label in FILES_ORDER:
        out.append(label)
    out.append("")
    out.append("")

    for fname, _label in FILES_ORDER:
        blocks = dict(file_blocks).get(fname)
        if blocks is None:
            continue
        out.append("")
        out.append("")
        prev_type = None
        for idx, b in enumerate(blocks):
            t = b["type"]
            if t == "heading":
                txt = clean_inline(b["text"])
                if not txt:
                    continue
                if prev_type is not None:
                    out.append("")
                out.append(txt)
                out.append("")
            elif t == "para":
                out.append(clean_inline(b["text"]))
                out.append("")
            elif t == "blockquote":
                txt = clean_inline(b["text"])
                if txt:
                    out.append(txt)
                    out.append("")
            elif t == "list_item":
                if b.get("ordered"):
                    num = to_arabic_numerals(b["number"])
                    out.append(f"{num}. {clean_inline(b['text'])}")
                else:
                    out.append(f"• {clean_inline(b['text'])}")
                next_type = blocks[idx + 1]["type"] if idx + 1 < len(blocks) else None
                if next_type != "list_item":
                    out.append("")
            elif t == "hr":
                out.append("")
            prev_type = t

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n\n", text)
    return text.strip() + "\n"


# ---------------------------------------------------------------------------
# توليد HTML (publish/book-final-ebook.html)
# ---------------------------------------------------------------------------

HTML_HEAD = """<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>{title} — {author}</title>
<meta name="author" content="{author}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  @page {{ size: A5; margin: 22mm 18mm; }}
  html {{ font-size: 17px; }}
  body {{
    font-family: "Amiri", "Scheherazade New", "Traditional Arabic", "Times New Roman", serif;
    line-height: 1.95;
    color: #111;
    background: #fff;
    max-width: 720px;
    margin: 0 auto;
    padding: 2rem 1.25rem 4rem;
    text-align: justify;
    direction: rtl;
  }}
  h1, h2, h3, h4 {{
    font-weight: 700;
    line-height: 1.4;
    margin: 1.6em 0 0.6em;
    text-align: right;
  }}
  h1 {{ font-size: 1.9rem; }}
  h2 {{ font-size: 1.5rem; }}
  h3 {{ font-size: 1.22rem; }}
  h4 {{ font-size: 1.08rem; }}
  p {{ margin: 0 0 1em; text-indent: 1.2em; }}
  blockquote {{
    margin: 1.2em 0;
    padding: 0.6em 1em;
    border-inline-start: 3px solid #999;
    background: #f6f6f4;
    text-indent: 0;
  }}
  ol, ul {{ margin: 0 0 1em; padding-inline-start: 1.6em; }}
  li {{ margin-bottom: 0.35em; text-indent: 0; }}
  hr {{ border: 0; border-top: 1px solid #bbb; margin: 2em auto; width: 60%; }}
  .cover {{
    min-height: 92vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    page-break-after: always;
  }}
  .cover .title {{ font-size: 3rem; font-weight: 800; margin-bottom: 0.4em; }}
  .cover .subtitle {{ font-size: 1.25rem; color: #333; max-width: 28em; line-height: 1.7; margin-bottom: 3em; }}
  .cover .author-label {{ color: #555; margin-bottom: 0.2em; }}
  .cover .author {{ font-size: 1.4rem; font-weight: 700; }}
  .toc {{ page-break-after: always; }}
  .toc h2 {{ text-align: center; }}
  .toc ol {{ list-style: none; padding: 0; }}
  .toc li {{ margin: 0.5em 0; font-size: 1.05rem; }}
  .toc a {{ color: #111; text-decoration: none; }}
  .toc a:hover {{ text-decoration: underline; }}
  .section {{ page-break-before: always; }}
  .section:first-of-type {{ page-break-before: auto; }}
  @media print {{
    body {{ max-width: none; padding: 0; }}
    a {{ color: inherit; text-decoration: none; }}
  }}
</style>
</head>
<body>
"""

HTML_TAIL = "\n</body>\n</html>\n"


def slugify(name: str) -> str:
    base = os.path.splitext(name)[0]
    return re.sub(r"[^a-zA-Z0-9-]+", "-", base).strip("-").lower()


def render_html_blocks(blocks: List[dict]) -> str:
    out: List[str] = []
    i = 0
    n = len(blocks)
    while i < n:
        b = blocks[i]
        t = b["type"]
        if t == "heading":
            level = min(max(b["level"], 1), 4)
            out.append(f"<h{level}>{html.escape(clean_inline(b['text']))}</h{level}>")
            i += 1
        elif t == "para":
            out.append(f"<p>{html.escape(clean_inline(b['text']))}</p>")
            i += 1
        elif t == "blockquote":
            out.append(f"<blockquote>{html.escape(clean_inline(b['text']))}</blockquote>")
            i += 1
        elif t == "hr":
            out.append("<hr>")
            i += 1
        elif t == "list_item":
            ordered = b.get("ordered", False)
            tag = "ol" if ordered else "ul"
            items = []
            while (
                i < n
                and blocks[i]["type"] == "list_item"
                and blocks[i].get("ordered", False) == ordered
            ):
                items.append(html.escape(clean_inline(blocks[i]["text"])))
                i += 1
            out.append(f"<{tag}>")
            for it in items:
                out.append(f"  <li>{it}</li>")
            out.append(f"</{tag}>")
        else:
            i += 1
    return "\n".join(out)


def build_html(file_blocks: List[Tuple[str, List[dict]]]) -> str:
    parts: List[str] = []
    parts.append(HTML_HEAD.format(
        title=html.escape(BOOK_TITLE),
        author=html.escape(AUTHOR),
    ))

    parts.append('<section class="cover">')
    parts.append(f'  <div class="title">{html.escape(BOOK_TITLE)}</div>')
    parts.append(f'  <div class="subtitle">{html.escape(BOOK_SUBTITLE)}</div>')
    parts.append('  <div class="author-label">تأليف</div>')
    parts.append(f'  <div class="author">{html.escape(AUTHOR)}</div>')
    parts.append('</section>')

    parts.append('<nav class="toc">')
    parts.append('  <h2>فهرس الكتاب</h2>')
    parts.append('  <ol>')
    fb = dict(file_blocks)
    for fname, label in FILES_ORDER:
        if fname in fb:
            parts.append(f'    <li><a href="#{slugify(fname)}">{html.escape(label)}</a></li>')
    parts.append('  </ol>')
    parts.append('</nav>')

    for fname, _label in FILES_ORDER:
        if fname not in fb:
            continue
        parts.append(f'<section class="section" id="{slugify(fname)}">')
        parts.append(render_html_blocks(fb[fname]))
        parts.append('</section>')

    parts.append(HTML_TAIL)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# نقطة الدخول
# ---------------------------------------------------------------------------

def main() -> None:
    PUBLISH_DIR.mkdir(exist_ok=True)

    file_blocks: List[Tuple[str, List[dict]]] = []
    for fname, _ in FILES_ORDER:
        path = CHAPTERS_DIR / fname
        if not path.exists():
            print(f"[تحذير] ملفّ مفقود: {path}")
            continue
        md = path.read_text(encoding="utf-8")
        cleaned = clean_chapter_source(md)
        file_blocks.append((fname, parse_blocks(cleaned)))

    md_out = build_clean_markdown(file_blocks)
    (PUBLISH_DIR / "book-final.md").write_text(md_out, encoding="utf-8")

    txt_out = build_print_text(file_blocks)
    (PUBLISH_DIR / "book-final-print.txt").write_text(txt_out, encoding="utf-8")

    html_out = build_html(file_blocks)
    (PUBLISH_DIR / "book-final-ebook.html").write_text(html_out, encoding="utf-8")

    print("تم بناء نسخة النشر في:", PUBLISH_DIR)


if __name__ == "__main__":
    main()
