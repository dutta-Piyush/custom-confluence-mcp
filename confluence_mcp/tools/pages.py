from __future__ import annotations

from confluence_mcp.app import mcp
from confluence_mcp.client import ConfluenceError, _client
from confluence_mcp.config import CONFLUENCE_URL
from confluence_mcp.utils import _format_page, _strip_html


@mcp.tool()
def get_page(page_id: str) -> str:
    """
    Get a Confluence page by its numeric ID.
    Returns the page title, space, URL, and body content as plain text.
    """
    url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}"
    params = {"expand": "body.storage,space,version,ancestors"}
    try:
        with _client() as client:
            resp = client.get(url, params=params)
        return _format_page(resp.json())
    except ConfluenceError as e:
        return f"ERROR: {e}"


@mcp.tool()
def search_confluence(cql: str, limit: int = 10) -> str:
    """
    Search Confluence using CQL (Confluence Query Language).

    Example CQL queries:
      - 'text ~ "submission letter"'               — full-text search
      - 'space = "SAP" AND type = "page"'           — pages in a space
      - 'creator = "jsmith" AND created > "2025-01-01"' — pages by user
      - 'title = "SLG Architecture"'                — exact title match
      - 'label = "gcp"'                             — pages with a label
    """
    url = f"{CONFLUENCE_URL}/rest/api/content/search"
    params = {"cql": cql, "limit": min(limit, 50), "expand": "space,version"}
    try:
        with _client() as client:
            resp = client.get(url, params=params)
            data = resp.json()
    except ConfluenceError as e:
        return f"ERROR: {e}"

    results = data.get("results", [])
    if not results:
        return f"No results found for CQL: {cql}"

    total = data.get("totalSize", len(results))
    lines = [f"Found {total} results (showing {len(results)}):\n"]
    for r in results:
        lines.append(
            f"  [{r.get('type', 'page')}] {r.get('title', 'Untitled')}\n"
            f"    Space: {r.get('space', {}).get('key', '?')} | "
            f"ID: {r.get('id', '?')} | v{r.get('version', {}).get('number', '?')}\n"
            f"    {CONFLUENCE_URL}{r.get('_links', {}).get('webui', '')}\n"
        )
    return "\n".join(lines)


@mcp.tool()
def get_page_by_title(space_key: str, title: str) -> str:
    """
    Find a Confluence page by its exact title within a space.
    Returns the full page content as plain text.
    """
    url = f"{CONFLUENCE_URL}/rest/api/content"
    params = {
        "spaceKey": space_key, "title": title,
        "expand": "body.storage,space,version,ancestors", "limit": 1,
    }
    try:
        with _client() as client:
            resp = client.get(url, params=params)
            data = resp.json()
    except ConfluenceError as e:
        return f"ERROR: {e}"

    results = data.get("results", [])
    if not results:
        return f"No page found with title '{title}' in space '{space_key}'"
    return _format_page(results[0])


@mcp.tool()
def get_space_pages(space_key: str, limit: int = 25) -> str:
    """List pages in a Confluence space. Returns titles, IDs, and URLs."""
    url = f"{CONFLUENCE_URL}/rest/api/content"
    params = {
        "spaceKey": space_key, "type": "page",
        "limit": min(limit, 100), "expand": "version", "orderby": "title",
    }
    try:
        with _client() as client:
            resp = client.get(url, params=params)
            data = resp.json()
    except ConfluenceError as e:
        return f"ERROR: {e}"

    results = data.get("results", [])
    if not results:
        return f"No pages found in space '{space_key}'"

    lines = [f"Space '{space_key}' — {data.get('size', len(results))} pages:\n"]
    for r in results:
        lines.append(
            f"  [{r.get('id', '?')}] {r.get('title', 'Untitled')} "
            f"(v{r.get('version', {}).get('number', '?')})  "
            f"{CONFLUENCE_URL}{r.get('_links', {}).get('webui', '')}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_page_children(page_id: str, limit: int = 25) -> str:
    """Get child pages of a given Confluence page. Useful for navigating hierarchies."""
    url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}/child/page"
    params = {"limit": min(limit, 100), "expand": "version"}
    try:
        with _client() as client:
            resp = client.get(url, params=params)
            data = resp.json()
    except ConfluenceError as e:
        return f"ERROR: {e}"

    results = data.get("results", [])
    if not results:
        return f"No child pages found for page ID {page_id}"

    lines = [f"Child pages of {page_id} ({len(results)} found):\n"]
    for r in results:
        lines.append(
            f"  [{r.get('id', '?')}] {r.get('title', 'Untitled')} "
            f"(v{r.get('version', {}).get('number', '?')})  "
            f"{CONFLUENCE_URL}{r.get('_links', {}).get('webui', '')}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_page_comments(page_id: str, limit: int = 20) -> str:
    """Get comments on a Confluence page."""
    url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}/child/comment"
    params = {"limit": min(limit, 50), "expand": "body.storage,version"}
    try:
        with _client() as client:
            resp = client.get(url, params=params)
            data = resp.json()
    except ConfluenceError as e:
        return f"ERROR: {e}"

    results = data.get("results", [])
    if not results:
        return f"No comments on page {page_id}"

    lines = [f"Comments on page {page_id} ({len(results)} found):\n"]
    for r in results:
        author = r.get("version", {}).get("by", {}).get("displayName", "Unknown")
        when = r.get("version", {}).get("when", "?")
        body_text = _strip_html(r.get("body", {}).get("storage", {}).get("value", ""))
        lines.append(f"  [{when}] {author}:\n    {body_text}\n")
    return "\n".join(lines)


@mcp.tool()
def get_page_tree(page_id: str, depth: int = 3) -> str:
    """
    Get the page hierarchy tree starting from a page ID or space key.
    Shows the structure with indentation, useful for understanding
    how documentation is organized before navigating to specific pages.

    Args:
        page_id: Page ID (numeric) or space key (e.g. "SAP")
        depth:   How many levels deep to traverse (1-5, default 3)
    """
    depth = max(1, min(depth, 5))
    lines: list[str] = []

    try:
        with _client() as client:
            if page_id.isdigit():
                resp = client.get(
                    f"{CONFLUENCE_URL}/rest/api/content/{page_id}",
                    params={"expand": "space,version"},
                )
                page = resp.json()
                lines.append(f"Page tree for: {page.get('title', page_id)} (ID: {page_id})\n")
                _build_tree(client, page_id, 0, depth, lines)
            else:
                resp = client.get(
                    f"{CONFLUENCE_URL}/rest/api/content",
                    params={"spaceKey": page_id, "type": "page", "depth": "root", "limit": 50, "expand": "version"},
                )
                root_pages = resp.json().get("results", [])
                lines.append(f"Page tree for space: {page_id} ({len(root_pages)} root pages)\n")
                for rp in root_pages:
                    lines.append(f"[{rp['id']}] {rp.get('title', '?')}")
                    _build_tree(client, rp["id"], 1, depth, lines)
    except ConfluenceError as e:
        return f"ERROR: {e}"

    return "\n".join(lines) if lines else f"No pages found for '{page_id}'"


def _build_tree(
    client: httpx.Client,
    page_id: str,
    level: int,
    max_depth: int,
    lines: list[str],
) -> None:
    if level >= max_depth:
        return
    try:
        resp = client.get(
            f"{CONFLUENCE_URL}/rest/api/content/{page_id}/child/page",
            params={"limit": 50, "expand": "version"},
        )
        children = resp.json().get("results", [])
        for child in children:
            indent = "  " * (level + 1)
            lines.append(f"{indent}├─ [{child['id']}] {child.get('title', '?')}")
            _build_tree(client, child["id"], level + 1, max_depth, lines)
    except ConfluenceError:
        pass


@mcp.tool()
def get_attachments(page_id: str) -> str:
    """
    List all attachments on a Confluence page.
    Returns filenames, sizes, media types, and download URLs.

    Args:
        page_id: Numeric page ID
    """
    try:
        with _client() as client:
            resp = client.get(
                f"{CONFLUENCE_URL}/rest/api/content/{page_id}/child/attachment",
                params={"limit": 100, "expand": "version"},
            )
            data = resp.json()
    except ConfluenceError as e:
        return f"ERROR: {e}"

    results = data.get("results", [])
    if not results:
        return f"No attachments on page {page_id}"

    lines = [f"Attachments on page {page_id} ({len(results)} found):\n"]
    for att in results:
        title = att.get("title", "?")
        size = att.get("extensions", {}).get("fileSize", 0)
        media = att.get("extensions", {}).get("mediaType", "?")
        dl = f"{CONFLUENCE_URL}{att.get('_links', {}).get('download', '')}"
        size_kb = size / 1024 if size else 0
        lines.append(f"  {title} ({size_kb:.1f} KB, {media})\n    ID: {att.get('id', '?')} | Download: {dl}")
    return "\n".join(lines)
