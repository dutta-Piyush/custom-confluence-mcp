from __future__ import annotations

import re

from confluence_mcp.app import mcp
from confluence_mcp.client import ConfluenceError, _client
from confluence_mcp.config import CONFLUENCE_URL
from confluence_mcp.utils import _strip_html


@mcp.tool()
def crawl_pages(query: str, space_key: str = "", max_pages: int = 10) -> str:
    """
    Smart crawl across Confluence to find pages matching a query.
    Searches using CQL full-text, then follows child pages and internal links
    to build a comprehensive view. Returns summaries of all discovered pages.

    Use this when you need to find information that might be spread across
    multiple pages, or when you're not sure which page contains the answer.

    Args:
        query:      What to search for (natural language or keywords)
        space_key:  Optional space to limit search (e.g. "SAP")
        max_pages:  Maximum pages to return (1-20, default 10)
    """
    max_pages = max(1, min(max_pages, 20))
    cql = f'text ~ "{query}"'
    if space_key:
        cql += f' AND space = "{space_key}"'
    cql += ' AND type = "page"'

    seen: set[str] = set()
    results: list[dict] = []
    try:
        with _client() as client:
            resp = client.get(
                f"{CONFLUENCE_URL}/rest/api/content/search",
                params={"cql": cql, "limit": min(max_pages, 20), "expand": "space,version,ancestors,body.storage"},
            )
            search_results = resp.json().get("results", [])

            for page in search_results:
                pid = page.get("id", "")
                if pid in seen or len(results) >= max_pages:
                    break
                seen.add(pid)
                body_text = _strip_html(page.get("body", {}).get("storage", {}).get("value", ""))
                results.append({
                    "id": pid,
                    "title": page.get("title", ""),
                    "space": page.get("space", {}).get("key", ""),
                    "url": f"{CONFLUENCE_URL}{page.get('_links', {}).get('webui', '')}",
                    "snippet": body_text[:500] + ("..." if len(body_text) > 500 else ""),
                })

                internal_ids = _extract_page_ids(page.get("body", {}).get("storage", {}).get("value", ""))
                for linked_id in internal_ids:
                    if linked_id in seen or len(results) >= max_pages:
                        break
                    seen.add(linked_id)
                    try:
                        lr = client.get(
                            f"{CONFLUENCE_URL}/rest/api/content/{linked_id}",
                            params={"expand": "space,version,body.storage"},
                        )
                        linked = lr.json()
                        linked_text = _strip_html(linked.get("body", {}).get("storage", {}).get("value", ""))
                        if query.lower() in linked_text.lower() or query.lower() in linked.get("title", "").lower():
                            results.append({
                                "id": linked_id,
                                "title": linked.get("title", ""),
                                "space": linked.get("space", {}).get("key", ""),
                                "url": f"{CONFLUENCE_URL}{linked.get('_links', {}).get('webui', '')}",
                                "snippet": linked_text[:500] + ("..." if len(linked_text) > 500 else ""),
                                "found_via": f"linked from page {pid}",
                            })
                    except ConfluenceError:
                        continue

                if len(results) < max_pages:
                    try:
                        cr = client.get(
                            f"{CONFLUENCE_URL}/rest/api/content/{pid}/child/page",
                            params={"limit": 5, "expand": "version"},
                        )
                        for child in cr.json().get("results", []):
                            cid = child.get("id", "")
                            if cid in seen or len(results) >= max_pages:
                                break
                            seen.add(cid)
                            try:
                                child_resp = client.get(
                                    f"{CONFLUENCE_URL}/rest/api/content/{cid}",
                                    params={"expand": "body.storage,space"},
                                )
                                child_data = child_resp.json()
                                child_text = _strip_html(child_data.get("body", {}).get("storage", {}).get("value", ""))
                                results.append({
                                    "id": cid,
                                    "title": child.get("title", ""),
                                    "space": child_data.get("space", {}).get("key", ""),
                                    "url": f"{CONFLUENCE_URL}{child.get('_links', {}).get('webui', '')}",
                                    "snippet": child_text[:500] + ("..." if len(child_text) > 500 else ""),
                                    "found_via": f"child of page {pid}",
                                })
                            except ConfluenceError:
                                continue
                    except ConfluenceError:
                        pass
    except ConfluenceError as e:
        return f"ERROR: {e}"

    if not results:
        return f"No pages found matching '{query}'" + (f" in space '{space_key}'" if space_key else "")

    lines = [f"Found {len(results)} pages for '{query}':\n"]
    for i, r in enumerate(results, 1):
        via = f" (via: {r['found_via']})" if r.get("found_via") else ""
        lines.append(
            f"--- [{i}] {r['title']}{via} ---\n"
            f"Space: {r['space']} | ID: {r['id']}\n"
            f"URL: {r['url']}\n"
            f"{r['snippet']}\n"
        )
    return "\n".join(lines)


def _extract_page_ids(html_content: str) -> list[str]:
    ids: list[str] = []
    for m in re.finditer(r'ri:content-id="(\d+)"', html_content):
        ids.append(m.group(1))
    for m in re.finditer(r'/pages/(\d+)/', html_content):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    return ids[:10]
