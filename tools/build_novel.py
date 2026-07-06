#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداة بناء نسختَي رواية «جود» الجاهزتَين للنشر من مسوّدات `drafts/`:

1) نسخة طباعة: نصّ عربيّ نظيفٌ بلا رموز ماركداون (#, -, _, *, >, ---, `).
2) نسخة إلكترونيّة: HTML مع صفحة عنوان تَحمل اسم المؤلف وفهرس الفصول.

تُحذف تلقائيًّا ملاحظاتُ المسوّدة التحريرية (الاقتباس التمهيديّ في رأس كل فصل)،
وتُحفَظ علامة فاصل المشهد ★ الفاصلة بين يوميات جود ومقطع الراوي العليم.

الاستعمال:
    python3 tools/build_novel.py

المخرجات تُكتب في مجلد novel/print/.
"""

from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = ROOT / "drafts"
PRINT_DIR = ROOT / "novel" / "print"

NOVEL_TITLE = "جود"
NOVEL_SUBTITLE = "رواية — مستلهَمةٌ من كتاب «كود الحياة»"
AUTHOR = "منجد محمد السيد"

# علامة فاصل المشهد بين يوميات جود (المتكلم) ومقطع الراوي العليم.
SCENE_BREAK = "★"

# ترتيب فصول الرواية في النسخة النهائية.
FILES_ORDER: List[Tuple[str, str]] = [
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
    ("chapter-13.md", "الفصل الثالث عشر"),
    ("chapter-14.md", "الفصل الرابع عشر"),
    ("chapter-15.md", "الفصل الخامس عشر"),
    ("chapter-16.md", "الفصل السادس عشر"),
    ("chapter-17.md", "الفصل السابع عشر"),
    ("chapter-18.md", "الفصل الثامن عشر"),
    ("chapter-19.md", "الفصل التاسع عشر"),
    ("chapter-20.md", "الفصل العشرون"),
    ("chapter-21.md", "الفصل الحادي والعشرون"),
    ("chapter-22.md", "الفصل الثاني والعشرون"),
    ("chapter-23.md", "الفصل الثالث والعشرون"),
    ("chapter-24.md", "الفصل الرابع والعشرون"),
]


# ---------------------------------------------------------------------------
# مُحلِّل ماركداون مبسَّط: يَستخرج بنيةً منطقيّة للنصّ ليَسهل تصديرها كنصّ عربيّ
# نظيف وكـHTML معًا.
# ---------------------------------------------------------------------------

# أنواع الكتل: heading, blockquote, list_item, hr, para, scene_break
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

        # سطر فارغ
        if stripped == "":
            flush_para()
            i += 1
            continue

        # علامة فاصل المشهد ★ (سطرٌ مستقلّ)
        if stripped == SCENE_BREAK:
            flush_para()
            blocks.append({"type": "scene_break"})
            i += 1
            continue

        # فاصل أفقي ---
        if re.fullmatch(r"-{3,}|_{3,}|\*{3,}", stripped):
            flush_para()
            blocks.append({"type": "hr"})
            i += 1
            continue

        # عنوان # ## ###
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            level = len(m.group(1))
            blocks.append({"type": "heading", "level": level, "text": m.group(2).strip()})
            i += 1
            continue

        # اقتباس >
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

        # عنصر قائمة مرقَّمة 1.  2.
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

        # عنصر قائمة غير مرقَّمة - أو *
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

        # فقرة عاديّة
        para_buf.append(stripped)
        i += 1

    flush_para()
    return blocks


def strip_editorial_notes(blocks: List[dict]) -> List[dict]:
    """يَحذف اقتباس ملاحظة المسوّدة التحريرية في رأس الفصل.

    الملاحظة هي أوّل كتلة اقتباس تَظهر قبل أيّ فقرةٍ سرديّة (بعد العنوان
    مباشرة). تُحذف حتى لا تَظهر في النسخة المنشورة، مع الإبقاء على أيّ
    اقتباساتٍ حقيقيّة قد تَرِد لاحقًا داخل السرد.
    """
    result: List[dict] = []
    dropped = False
    seen_para = False
    for b in blocks:
        if b["type"] == "para":
            seen_para = True
        if (
            not dropped
            and not seen_para
            and b["type"] == "blockquote"
        ):
            dropped = True
            continue
        result.append(b)
    return result


# ---------------------------------------------------------------------------
# تنظيف النصّ السطريّ من بقايا الرموز (مائل، عريض، شرطة سفلية، باكتيك)
# ---------------------------------------------------------------------------

def clean_inline(text: str) -> str:
    """يَحذف رموز التنسيق السطريّة مع الإبقاء على المحتوى."""
    if not text:
        return text
    s = text

    # روابط [نص](رابط) → نص
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)

    # عريض/مائل: ***x***, **x**, *x*, ___x___, __x__, _x_
    for _ in range(3):
        s = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", s)
        s = re.sub(r"___(.+?)___", r"\1", s)
        s = re.sub(r"__(.+?)__", r"\1", s)
        s = re.sub(r"(?<!_)_(?!_)([^_]+?)(?<!_)_(?!_)", r"\1", s)

    # كود سطريّ `x`
    s = re.sub(r"`([^`]+)`", r"\1", s)

    # حذف أيّ شَرطات سفليّة أو نجوم أو باكتيك متبقّية
    s = s.replace("_", "")
    s = s.replace("*", "")
    s = s.replace("`", "")

    # تَنظيف المسافات
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s


def to_arabic_numerals(n: int) -> str:
    table = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
    return str(n).translate(table)


# ---------------------------------------------------------------------------
# تَوليد نصّ الطباعة (TXT) من قائمة الكتل
# ---------------------------------------------------------------------------

def blocks_to_print_text(file_blocks: List[Tuple[str, List[dict]]]) -> str:
    fb = dict(file_blocks)
    out: List[str] = []
    out.append(NOVEL_TITLE)
    out.append("")
    out.append(NOVEL_SUBTITLE)
    out.append("")
    out.append(f"تأليف: {AUTHOR}")
    out.append("")
    out.append("")
    out.append("فهرس الرواية")
    out.append("")
    for fname, label in FILES_ORDER:
        if fname in fb:
            out.append(label)
    out.append("")
    out.append("")

    for fname, _ in FILES_ORDER:
        if fname not in fb:
            continue
        blocks = fb[fname]
        # فاصل بصريّ بين الفصول دون رموز
        out.append("")
        out.append("")

        prev_type = None
        for idx, b in enumerate(blocks):
            t = b["type"]
            if t == "heading":
                text = clean_inline(b["text"])
                if not text:
                    continue
                if prev_type is not None:
                    out.append("")
                out.append(text)
                out.append("")
            elif t == "para":
                out.append(clean_inline(b["text"]))
                out.append("")
            elif t == "scene_break":
                out.append(SCENE_BREAK)
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
# تَوليد HTML للنسخة الإلكترونيّة
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
  .scene-break {{
    text-align: center;
    text-indent: 0;
    margin: 1.6em 0;
    color: #666;
    letter-spacing: 0.3em;
  }}
  blockquote {{
    margin: 1.2em 0;
    padding: 0.6em 1em;
    border-inline-start: 3px solid #999;
    background: #f6f6f4;
    font-style: normal;
    text-indent: 0;
  }}
  ol, ul {{ margin: 0 0 1em; padding-inline-start: 1.6em; }}
  li {{ margin-bottom: 0.35em; text-indent: 0; }}
  hr {{
    border: 0;
    border-top: 1px solid #bbb;
    margin: 2em auto;
    width: 60%;
  }}
  .cover {{
    min-height: 92vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    page-break-after: always;
  }}
  .cover .title {{
    font-size: 3.4rem;
    font-weight: 800;
    margin-bottom: 0.4em;
  }}
  .cover .subtitle {{
    font-size: 1.25rem;
    color: #333;
    max-width: 28em;
    line-height: 1.7;
    margin-bottom: 3em;
  }}
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
        elif t == "scene_break":
            out.append(f'<p class="scene-break">{html.escape(SCENE_BREAK)}</p>')
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
            while i < n and blocks[i]["type"] == "list_item" and blocks[i].get("ordered", False) == ordered:
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
    fb = dict(file_blocks)
    parts: List[str] = []
    parts.append(HTML_HEAD.format(
        title=html.escape(NOVEL_TITLE),
        author=html.escape(AUTHOR),
    ))

    # صفحة العنوان
    parts.append('<section class="cover">')
    parts.append(f'  <div class="title">{html.escape(NOVEL_TITLE)}</div>')
    parts.append(f'  <div class="subtitle">{html.escape(NOVEL_SUBTITLE)}</div>')
    parts.append('  <div class="author-label">تأليف</div>')
    parts.append(f'  <div class="author">{html.escape(AUTHOR)}</div>')
    parts.append('</section>')

    # فهرس
    parts.append('<nav class="toc">')
    parts.append('  <h2>فهرس الرواية</h2>')
    parts.append('  <ol>')
    for fname, label in FILES_ORDER:
        if fname in fb:
            parts.append(f'    <li><a href="#{slugify(fname)}">{html.escape(label)}</a></li>')
    parts.append('  </ol>')
    parts.append('</nav>')

    # محتوى الفصول
    for fname, _ in FILES_ORDER:
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
    PRINT_DIR.mkdir(parents=True, exist_ok=True)

    file_blocks: List[Tuple[str, List[dict]]] = []
    for fname, _ in FILES_ORDER:
        path = DRAFTS_DIR / fname
        if not path.exists():
            print(f"[تحذير] ملفّ مفقود: {path}")
            continue
        md = path.read_text(encoding="utf-8")
        blocks = strip_editorial_notes(parse_blocks(md))
        file_blocks.append((fname, blocks))

    # 1) نسخة الطباعة (TXT)
    txt_out = blocks_to_print_text(file_blocks)
    (PRINT_DIR / "novel-print.txt").write_text(txt_out, encoding="utf-8")

    # 2) النسخة الإلكترونيّة (HTML)
    html_out = build_html(file_blocks)
    (PRINT_DIR / "novel-ebook.html").write_text(html_out, encoding="utf-8")

    print("تم بناء نسختَي الرواية في:", PRINT_DIR)


if __name__ == "__main__":
    main()
