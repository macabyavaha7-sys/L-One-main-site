import html
import json
import re
from collections.abc import Callable
from urllib.parse import urlparse

import bleach


SUPPORTED_TYPES = {
    "paragraph", "heading", "quote", "list", "image", "gallery", "video",
    "divider", "code", "attachment", "external_link",
}
MEDIA_ID = re.compile(r"^[a-f0-9]{32}$")
MAX_DOCUMENT_BYTES = 500_000


class BlockValidationError(ValueError):
    pass


def _clean_text(value, limit: int = 100_000) -> str:
    if not isinstance(value, str):
        raise BlockValidationError("Text values must be strings")
    if len(value) > limit:
        raise BlockValidationError("Text value is too large")
    return bleach.clean(value, tags=[], attributes={}, strip=True).strip()


def _safe_url(value: str, external: bool = False) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise BlockValidationError("Invalid URL")
    parsed = urlparse(value.strip())
    allowed = {"http", "https"} if external else {"", "http", "https"}
    if parsed.scheme.lower() not in allowed:
        raise BlockValidationError("Unsafe URL")
    if external and not parsed.netloc:
        raise BlockValidationError("External URL must be absolute")
    return value.strip()


def _media_id(value) -> str:
    if not isinstance(value, str) or not MEDIA_ID.fullmatch(value):
        raise BlockValidationError("Invalid media ID")
    return value


def normalize_blocks(raw: list[dict]) -> list[dict]:
    if not isinstance(raw, list) or len(raw) > 500:
        raise BlockValidationError("Body must be a block list")
    if len(json.dumps(raw, ensure_ascii=False).encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise BlockValidationError("Document is too large")
    normalized = []
    for source in raw:
        if not isinstance(source, dict) or source.get("type") not in SUPPORTED_TYPES:
            raise BlockValidationError("Unknown block type")
        kind = source["type"]
        block = {"type": kind}
        if kind in {"paragraph", "quote"}:
            block["text"] = _clean_text(source.get("text", ""))
        elif kind == "heading":
            level = source.get("level", 2)
            if level not in {2, 3, 4}:
                raise BlockValidationError("Invalid heading level")
            block.update(level=level, text=_clean_text(source.get("text", ""), 500))
        elif kind == "list":
            items = source.get("items")
            if not isinstance(items, list) or len(items) > 100 or any(not isinstance(item, str) for item in items):
                raise BlockValidationError("Invalid list items")
            block.update(ordered=bool(source.get("ordered", False)), items=[_clean_text(item, 2000) for item in items])
        elif kind in {"image", "video", "attachment"}:
            block["media_id"] = _media_id(source.get("media_id"))
            block["alt"] = _clean_text(source.get("alt", ""), 500)
        elif kind == "gallery":
            ids = source.get("media_ids")
            if not isinstance(ids, list) or not ids or len(ids) > 50:
                raise BlockValidationError("Invalid gallery")
            block["media_ids"] = [_media_id(value) for value in ids]
        elif kind == "code":
            block.update(language=_clean_text(source.get("language", "text"), 40), code=_clean_text(source.get("code", "")))
        elif kind == "external_link":
            block.update(url=_safe_url(source.get("url", ""), external=True), text=_clean_text(source.get("text", ""), 500))
        normalized.append(block)
    return normalized


def _media(media_lookup: Callable[[str], dict | None], media_id: str) -> dict:
    value = media_lookup(media_id)
    if not value or not value.get("public_url"):
        raise BlockValidationError(f"Media is unavailable: {media_id}")
    return value


def render_blocks(blocks: list[dict], media_lookup: Callable[[str], dict | None]) -> str:
    parts = []
    for block in normalize_blocks(blocks):
        kind = block["type"]
        if kind == "paragraph":
            parts.append(f"<p>{html.escape(block['text'])}</p>")
        elif kind == "heading":
            parts.append(f"<h{block['level']}>{html.escape(block['text'])}</h{block['level']}>")
        elif kind == "quote":
            parts.append(f"<blockquote>{html.escape(block['text'])}</blockquote>")
        elif kind == "list":
            tag = "ol" if block["ordered"] else "ul"
            items = "".join(f"<li>{html.escape(item)}</li>" for item in block["items"])
            parts.append(f"<{tag}>{items}</{tag}>")
        elif kind == "image":
            media = _media(media_lookup, block["media_id"])
            parts.append(f'<figure><img src="{html.escape(media["public_url"], quote=True)}" alt="{html.escape(block["alt"], quote=True)}" loading="lazy"></figure>')
        elif kind == "video":
            media = _media(media_lookup, block["media_id"])
            parts.append(f'<video src="{html.escape(media["public_url"], quote=True)}" controls preload="metadata"></video>')
        elif kind == "attachment":
            media = _media(media_lookup, block["media_id"])
            label = block["alt"] or media.get("original_name") or "下载附件"
            parts.append(f'<a href="{html.escape(media["public_url"], quote=True)}" download>{html.escape(label)}</a>')
        elif kind == "gallery":
            images = []
            for media_id in block["media_ids"]:
                media = _media(media_lookup, media_id)
                images.append(f'<img src="{html.escape(media["public_url"], quote=True)}" alt="" loading="lazy">')
            parts.append(f'<div class="content-gallery">{"".join(images)}</div>')
        elif kind == "divider":
            parts.append("<hr>")
        elif kind == "code":
            parts.append(f'<pre><code class="language-{html.escape(block["language"], quote=True)}">{html.escape(block["code"])}</code></pre>')
        elif kind == "external_link":
            parts.append(f'<p><a href="{html.escape(block["url"], quote=True)}" rel="noopener noreferrer">{html.escape(block["text"] or block["url"])}</a></p>')
    rendered = "".join(parts)
    return bleach.clean(
        rendered,
        tags={"p", "h2", "h3", "h4", "blockquote", "ol", "ul", "li", "figure", "img", "video", "a", "div", "hr", "pre", "code"},
        attributes={"img": ["src", "alt", "loading"], "video": ["src", "controls", "preload"], "a": ["href", "rel", "download"], "div": ["class"], "code": ["class"]},
        protocols={"http", "https"},
        strip=True,
    )


def excerpt_from_blocks(blocks: list[dict], limit: int = 180) -> str:
    texts = []
    for block in normalize_blocks(blocks):
        if "text" in block:
            texts.append(block["text"])
        elif block["type"] == "list":
            texts.extend(block["items"])
    value = " ".join(filter(None, texts)).strip()
    return value if len(value) <= limit else value[: max(0, limit - 1)].rstrip() + "…"
