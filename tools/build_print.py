#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداة بناء نسختَي الكتاب الجاهزتَين للنشر:

1) نسخة طباعة: نصّ عربيّ نظيفٌ بلا رموز ماركداون (#, -, _, *, >, ---, `).
2) نسخة إلكترونيّة: HTML مع صفحة عنوان تَحمل اسم المؤلف.

الاستعمال:
    python3 tools/build_print.py

المخرجات تُكتب في مجلد print/.
"""

from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# إعادة استخدام مراحل تنظيف المصدر من أداة النشر لضمان اتّساق المُخرجَين:
# حذف قسم «ملاحظات تحريريّة للمراجعة»، وعلامات الحواشي، والمراجع الداخليّة.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_publish import clean_chapter_source  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHAPTERS_DIR = ROOT / "chapters"
PRINT_DIR = ROOT / "print"

BOOK_TITLE = "كود الحياة"
BOOK_SUBTITLE = "من النظام إلى الخالق، ومن الخالق إلى معنى الإنسان وفعله"
AUTHOR = "منجد محمد السيد"

# ترتيب الملفات في الكتاب النهائي
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
    ("appendix-b-symbolic-code.md", "الملحق ب"),
    ("conclusion.md", "خاتمة الكتاب"),
    ("scientific-references.md", "المراجع العلميّة"),
]


# ---------------------------------------------------------------------------
# مُحلِّل ماركداون مبسَّط: يَستخرج بنيةً منطقيّة للنصّ ليَسهل تصديرها كنصّ عربيّ
# نظيف وكـHTML معًا.
# ---------------------------------------------------------------------------

# أنواع الكتل: heading, blockquote, list_item_ol, list_item_ul, hr, para, blank
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
            seg = [s for s in quote_lines]
            label = None
            # وسمٌ وظيفيٌّ مستقلٌّ على أوّل سطر: **نص** وحده (مثل «بعبارة أبسط»)
            # يَتلوه جسمُ الاقتباس. يُفصَل لئلا يَلتحم بالجملة التالية عند التسطيح.
            # أمّا السطرُ العريضُ الذي لا جسمَ بعده (جملةٌ مُبرَزةٌ قائمةٌ بذاتها)
            # فلا يُعدّ وسمًا، ويَبقى نصًّا كما هو.
            first = seg[0].strip() if seg else ""
            m_label = re.fullmatch(r"\*\*(.+?)\*\*", first)
            rest = [s for s in seg[1:] if s]
            if m_label and rest:
                label = m_label.group(1).strip()
                seg = seg[1:]
            text = " ".join(s for s in seg if s).strip()
            blocks.append({"type": "blockquote", "label": label, "text": text})
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
    # نَستعمل تَكرارًا للتعامل مع التداخل
    for _ in range(3):
        s = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", s)
        s = re.sub(r"___(.+?)___", r"\1", s)
        s = re.sub(r"__(.+?)__", r"\1", s)
        s = re.sub(r"(?<!_)_(?!_)([^_]+?)(?<!_)_(?!_)", r"\1", s)

    # كود سطريّ `x`
    s = re.sub(r"`([^`]+)`", r"\1", s)

    # شَرطة طويلة — تَبقى كما هي لأنها ليست رمزَ ماركداون بل علامة ترقيم.
    # لكن نَحذف أيّ شَرطات سفليّة منعزلة _ والنجوم * المتبقية.
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

    for fname, label in file_blocks_iter_order(file_blocks):
        blocks = dict(file_blocks)[fname]
        # فاصل بصريّ بين الأقسام دون رموز
        out.append("")
        out.append("")

        # أوّل عنوان h1/h2 يَحلّ محل عنوان القسم؛ إن لم يوجد نَستعمل التسمية.
        rendered_first_heading = False
        prev_type = None

        for b in blocks:
            t = b["type"]
            if t == "heading":
                text = clean_inline(b["text"])
                if not text:
                    continue
                # سطر فارغ قبل العنوان
                if prev_type is not None:
                    out.append("")
                out.append(text)
                out.append("")
                rendered_first_heading = True
            elif t == "para":
                out.append(clean_inline(b["text"]))
                out.append("")
            elif t == "blockquote":
                # نَكتب الاقتباس على سطره دون أيّ رمز إضافيّ
                label = b.get("label")
                txt = clean_inline(b["text"])
                if label:
                    lbl = clean_inline(label)
                    # الوسم على سطرٍ مستقلٍّ؛ يُذيَّل بنقطتين ما لم يَكن مُنتهيًا
                    # بعلامة ترقيمٍ أصلًا (كالجملة المُبرَزة القائمة بذاتها).
                    if lbl and lbl[-1] in "؟!.:؛…،":
                        out.append(lbl)
                    else:
                        out.append(f"{lbl}:")
                    if txt:
                        out.append(txt)
                    out.append("")
                elif txt:
                    out.append(txt)
                    out.append("")
            elif t == "list_item":
                if b.get("ordered"):
                    num = to_arabic_numerals(b["number"])
                    out.append(f"{num}. {clean_inline(b['text'])}")
                else:
                    out.append(f"• {clean_inline(b['text'])}")
                # سطر فارغ بعد آخر عنصر قائمة عند تغيُّر النوع
                next_type = blocks[blocks.index(b) + 1]["type"] if blocks.index(b) + 1 < len(blocks) else None
                if next_type != "list_item":
                    out.append("")
            elif t == "hr":
                # فاصل بسيط بأسطر فارغة بدلًا من أيّ رمز
                out.append("")
            prev_type = t

        # تَنظيف الأسطر الفارغة المتراكمة
    # إزالة أكثر من سطرَين فارغَين متتاليَين
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n\n", text)
    return text.strip() + "\n"


def file_blocks_iter_order(file_blocks):
    seen = set()
    for fname, _ in FILES_ORDER:
        if fname in dict(file_blocks) and fname not in seen:
            yield fname, fname
            seen.add(fname)


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
  blockquote {{
    margin: 1.2em 0;
    padding: 0.6em 1em;
    border-inline-start: 3px solid #999;
    background: #f6f6f4;
    font-style: normal;
    text-indent: 0;
  }}
  blockquote p {{ margin: 0 0 0.5em; text-indent: 0; }}
  blockquote p:last-child {{ margin-bottom: 0; }}
  blockquote .quote-label {{ font-weight: 700; margin-bottom: 0.2em; }}
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
    font-size: 3rem;
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
    # صنع مُعرِّفٍ بسيط من اسم الملف
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
            label = b.get("label")
            txt = html.escape(clean_inline(b["text"]))
            if label:
                lbl = html.escape(clean_inline(label))
                out.append(
                    f"<blockquote><p class=\"quote-label\"><strong>{lbl}</strong></p><p>{txt}</p></blockquote>"
                )
            else:
                out.append(f"<blockquote>{txt}</blockquote>")
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
    parts: List[str] = []
    parts.append(HTML_HEAD.format(
        title=html.escape(BOOK_TITLE),
        author=html.escape(AUTHOR),
    ))

    # صفحة العنوان
    parts.append('<section class="cover">')
    parts.append(f'  <div class="title">{html.escape(BOOK_TITLE)}</div>')
    parts.append(f'  <div class="subtitle">{html.escape(BOOK_SUBTITLE)}</div>')
    parts.append('  <div class="author-label">تأليف</div>')
    parts.append(f'  <div class="author">{html.escape(AUTHOR)}</div>')
    parts.append('</section>')

    # فهرس
    parts.append('<nav class="toc">')
    parts.append('  <h2>فهرس الكتاب</h2>')
    parts.append('  <ol>')
    for fname, label in FILES_ORDER:
        if fname in dict(file_blocks):
            parts.append(f'    <li><a href="#{slugify(fname)}">{html.escape(label)}</a></li>')
    parts.append('  </ol>')
    parts.append('</nav>')

    # محتوى الأقسام
    fb = dict(file_blocks)
    for fname, label in FILES_ORDER:
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
    PRINT_DIR.mkdir(exist_ok=True)

    file_blocks: List[Tuple[str, List[dict]]] = []
    for fname, _ in FILES_ORDER:
        path = CHAPTERS_DIR / fname
        if not path.exists():
            print(f"[تحذير] ملفّ مفقود: {path}")
            continue
        md = path.read_text(encoding="utf-8")
        md = clean_chapter_source(md)
        file_blocks.append((fname, parse_blocks(md)))

    # 1) نسخة الطباعة (TXT)
    txt_out = blocks_to_print_text(file_blocks)
    (PRINT_DIR / "book-print.txt").write_text(txt_out, encoding="utf-8")

    # 2) النسخة الإلكترونيّة (HTML)
    html_out = build_html(file_blocks)
    (PRINT_DIR / "book-ebook.html").write_text(html_out, encoding="utf-8")

    print("تم بناء النسختَين في:", PRINT_DIR)


if __name__ == "__main__":
    main()
