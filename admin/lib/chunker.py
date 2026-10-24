"""Stage 1: split a document into retrieval-sized chunks that keep their section heading."""
import re


def words(s):
    return s.split()


def html_to_text(html):
    h = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", str(html), flags=re.I)
    h = re.sub(r"<h([1-6])[^>]*>([\s\S]*?)</h\1>",
               lambda m: f"\n\n{'#' * int(m.group(1))} {re.sub(r'<[^>]+>', '', m.group(2))}\n\n", h, flags=re.I)
    h = re.sub(r"</(p|div|li|tr|blockquote|pre)>|<br\s*/?>", "\n\n", h, flags=re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    for a, b in (("&nbsp;", " "), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&amp;", "&")):
        h = h.replace(a, b)
    h = re.sub(r"[ \t]+", " ", h)
    return re.sub(r"\n{3,}", "\n\n", h).strip()


def _split_long(block, target):
    out = []
    for part in [p for p in re.split(r"(?<=[.!?])\s+|\n", block) if p]:
        w = words(part)
        if len(w) <= target * 1.5:
            out.append(part)
        else:
            out += [" ".join(w[i:i + target]) for i in range(0, len(w), target)]
    return out


def chunk(text, target=180, overlap=30):
    """target = words per chunk; overlap = words repeated at the start of the next chunk."""
    chunks, heading, cur_heading, cur, cur_words = [], "", "", [], 0

    def emit(keep_tail):
        nonlocal cur, cur_words, cur_heading
        if not cur:
            return
        body = "\n".join(cur).strip()
        if len(words(body)) >= 5:
            chunks.append({"heading": cur_heading, "text": body})
        tail = " ".join(words(body)[-overlap:]) if keep_tail else ""
        cur = [tail] if tail else []
        cur_words = len(words(tail))
        cur_heading = heading

    for raw in re.split(r"\n{2,}", text):
        block = raw.strip()
        if not block:
            continue
        m = re.match(r"^#{1,6}\s+(.+)$", block)
        if m and "\n" not in block:          # a heading starts a new section
            emit(False)
            heading = cur_heading = m.group(1).strip()
            continue
        pieces = _split_long(block, target) if len(words(block)) > target * 1.5 else [block]
        for piece in pieces:
            w = len(words(piece))
            if cur_words + w > target and cur_words > 0:
                emit(True)
            cur.append(piece)
            cur_words += w
    emit(False)
    return chunks
