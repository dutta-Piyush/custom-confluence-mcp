from __future__ import annotations

import html
import re

from confluence_mcp.config import CONFLUENCE_URL


def _strip_html(raw_html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<(br|/p|/div|/tr|/li|/h[1-6])[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _format_page(data: dict) -> str:
    title = data.get("title", "Untitled")
    space_key = data.get("space", {}).get("key", "?")
    version = data.get("version", {}).get("number", "?")
    body_html = data.get("body", {}).get("storage", {}).get("value", "")
    page_url = f"{CONFLUENCE_URL}{data.get('_links', {}).get('webui', '')}"
    page_id = data.get("id", "?")

    body_text = _strip_html(body_html)

    ancestors = " > ".join(a.get("title", "") for a in data.get("ancestors", []))
    breadcrumb = f"Path: {ancestors} > {title}" if ancestors else f"Page: {title}"

    return (
        f"{breadcrumb}\n"
        f"Space: {space_key} | ID: {page_id} | Version: {version}\n"
        f"URL: {page_url}\n"
        f"{'=' * 60}\n\n"
        f"{body_text}"
    )


def _xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
