"""Load a folder of markdown files and split it into passages."""

import os
import re
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,3})\s+(.*\S)\s*$")


def _unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def parse_tags(value):
    """'a, b' or '[a, b]' -> ['a', 'b']."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [t for t in (_unquote(x) for x in value.split(",")) if t]


def parse_frontmatter(text):
    """Return (meta, body). Without a closed '---' block, meta is empty."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            meta = {}
            for line in lines[1:end]:
                key, sep, value = line.partition(":")
                if sep and key.strip():
                    meta[key.strip().lower()] = _unquote(value)
            return meta, "\n".join(lines[end + 1:])
    return {}, text


def split_sections(body):
    """Split at #, ##, ### headings (outside code fences).

    Returns a list of (level, heading, text). Text before the first heading
    has level 0 and an empty heading.
    """
    sections = []
    level, heading, buf = 0, "", []
    in_fence = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else HEADING_RE.match(line)
        if match:
            sections.append((level, heading, "\n".join(buf)))
            level, heading, buf = len(match.group(1)), match.group(2), []
        else:
            buf.append(line)
    sections.append((level, heading, "\n".join(buf)))
    return sections


def chunk(text, max_chars):
    """Split text on paragraph boundaries into chunks of at most max_chars.

    A single paragraph longer than max_chars stands alone.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        if current and len(current) + 2 + len(para) > max_chars:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


def parse_document(text, doc_id, default_sensitivity="internal", max_chars=1500):
    """Turn one markdown document into a list of passage dicts."""
    meta, body = parse_frontmatter(text.lstrip("﻿"))
    sections = split_sections(body)
    title = meta.get("title") or next(
        (h for lvl, h, _ in sections if lvl == 1), Path(doc_id).stem
    )
    base = {
        "doc_id": doc_id,
        "title": title,
        "sensitivity": (meta.get("sensitivity") or default_sensitivity).strip().lower(),
        "source": meta.get("source", ""),
        "updated": meta.get("updated", ""),
        "tags": parse_tags(meta.get("tags", "")),
    }
    passages = []
    for _, heading, section_text in sections:
        for piece in chunk(section_text, max_chars):
            passages.append(dict(base, heading=heading, text=piece))
    return passages


def load_corpus(root, default_sensitivity="internal", max_chars=1500):
    """Walk root for *.md, skipping names that start with '.' or '_'."""
    if not os.path.isdir(root):
        raise NotADirectoryError(f"corpus directory not found: {root}")
    passages = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith((".", "_")))
        for name in sorted(filenames):
            if name.startswith((".", "_")) or not name.endswith(".md"):
                continue
            path = os.path.join(dirpath, name)
            doc_id = Path(os.path.relpath(path, root)).as_posix()
            with open(path, encoding="utf-8") as f:
                passages.extend(
                    parse_document(f.read(), doc_id, default_sensitivity, max_chars)
                )
    return passages
