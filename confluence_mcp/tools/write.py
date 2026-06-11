from __future__ import annotations

from confluence_mcp.app import mcp
from confluence_mcp.client import ConfluenceError, _client
from confluence_mcp.config import CONFLUENCE_PAT, CONFLUENCE_URL, VERIFY_SSL


@mcp.tool()
def update_page(page_id: str, new_content: str, message: str = "Updated via MCP") -> str:
    """
    REPLACE an existing Confluence page's entire content with new content.
    WARNING: This replaces ALL existing content. To add content without
    losing what's already there, use append_to_page or prepend_to_page instead.

    Args:
        page_id:     Numeric page ID (e.g. "504270225")
        new_content: Complete new page body. Can be:
                     - Plain text (auto-wrapped in <p> tags)
                     - XHTML storage format (<p>, <h1>-<h6>, <table>, <ul>, etc.)
        message:     Version comment shown in page history.
    """
    content = new_content.strip()
    if not content.startswith("<"):
        content = "".join(f"<p>{line}</p>" for line in content.split("\n") if line.strip())
    try:
        with _client() as client:
            resp = client.get(
                f"{CONFLUENCE_URL}/rest/api/content/{page_id}",
                params={"expand": "version,space"},
            )
            current = resp.json()
            title = current["title"]
            version = current["version"]["number"]
            payload = {
                "id": page_id,
                "type": "page",
                "title": title,
                "body": {"storage": {"value": content, "representation": "storage"}},
                "version": {"number": version + 1, "message": message},
            }
            resp = client.put(
                f"{CONFLUENCE_URL}/rest/api/content/{page_id}",
                json=payload,
            )
            result = resp.json()
    except ConfluenceError as e:
        return f"ERROR: {e}"
    new_ver = result["version"]["number"]
    page_url = f"{CONFLUENCE_URL}{result['_links']['webui']}"
    return f"Updated '{title}' (v{version} → v{new_ver})\nURL: {page_url}"


@mcp.tool()
def prepend_to_page(page_id: str, content_to_add: str, message: str = "Prepended via MCP") -> str:
    """
    Add content to the TOP of an existing Confluence page, keeping all existing content.
    Use this when asked to "add something to the top/beginning of the page".

    Args:
        page_id:        Numeric page ID
        content_to_add: Content to insert at the top. Can be plain text or XHTML.
        message:        Version comment shown in page history.
    """
    new_html = content_to_add.strip()
    if not new_html.startswith("<"):
        new_html = "".join(f"<p>{line}</p>" for line in new_html.split("\n") if line.strip())
    try:
        with _client() as client:
            resp = client.get(
                f"{CONFLUENCE_URL}/rest/api/content/{page_id}",
                params={"expand": "body.storage,version,space"},
            )
            current = resp.json()
            title = current["title"]
            version = current["version"]["number"]
            existing_body = current["body"]["storage"]["value"]
            combined = f"{new_html}\n{existing_body}"
            payload = {
                "id": page_id,
                "type": "page",
                "title": title,
                "body": {"storage": {"value": combined, "representation": "storage"}},
                "version": {"number": version + 1, "message": message},
            }
            resp = client.put(
                f"{CONFLUENCE_URL}/rest/api/content/{page_id}",
                json=payload,
            )
            result = resp.json()
    except ConfluenceError as e:
        return f"ERROR: {e}"
    new_ver = result["version"]["number"]
    page_url = f"{CONFLUENCE_URL}{result['_links']['webui']}"
    return f"Prepended to '{title}' (v{version} → v{new_ver})\nURL: {page_url}"


@mcp.tool()
def append_to_page(page_id: str, content_to_add: str, message: str = "Appended via MCP") -> str:
    """
    Add content to the BOTTOM of an existing Confluence page, keeping all existing content.
    Use this when asked to "add something to the page" or "append to the page".

    Args:
        page_id:        Numeric page ID
        content_to_add: Content to add at the bottom. Can be plain text or XHTML.
        message:        Version comment shown in page history.
    """
    new_html = content_to_add.strip()
    if not new_html.startswith("<"):
        new_html = "".join(f"<p>{line}</p>" for line in new_html.split("\n") if line.strip())
    try:
        with _client() as client:
            resp = client.get(
                f"{CONFLUENCE_URL}/rest/api/content/{page_id}",
                params={"expand": "body.storage,version,space"},
            )
            current = resp.json()
            title = current["title"]
            version = current["version"]["number"]
            existing_body = current["body"]["storage"]["value"]
            combined = f"{existing_body}\n{new_html}"
            payload = {
                "id": page_id,
                "type": "page",
                "title": title,
                "body": {"storage": {"value": combined, "representation": "storage"}},
                "version": {"number": version + 1, "message": message},
            }
            resp = client.put(
                f"{CONFLUENCE_URL}/rest/api/content/{page_id}",
                json=payload,
            )
            result = resp.json()
    except ConfluenceError as e:
        return f"ERROR: {e}"
    new_ver = result["version"]["number"]
    page_url = f"{CONFLUENCE_URL}{result['_links']['webui']}"
    return f"Appended to '{title}' (v{version} → v{new_ver})\nURL: {page_url}"


@mcp.tool()
def create_page(space_key: str, title: str, content: str, parent_id: str = "") -> str:
    """
    Create a new Confluence page.

    Args:
        space_key:  Space key (e.g. "SAP", "AI4CF")
        title:      Page title
        content:    Page body in Confluence storage format (XHTML) or plain text.
        parent_id:  Optional parent page ID to create as a child page.

    Returns confirmation with page ID and URL.
    """
    body = content.strip()
    if not body.startswith("<"):
        body = "".join(f"<p>{line}</p>" for line in body.split("\n") if line.strip())

    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {"storage": {"value": body, "representation": "storage"}},
    }
    if parent_id:
        payload["ancestors"] = [{"id": parent_id}]
    try:
        with _client() as client:
            resp = client.post(
                f"{CONFLUENCE_URL}/rest/api/content",
                json=payload,
            )
            result = resp.json()
    except ConfluenceError as e:
        return f"ERROR: {e}"
    page_id = result["id"]
    page_url = f"{CONFLUENCE_URL}{result['_links']['webui']}"
    return f"Created '{title}' (ID: {page_id})\nURL: {page_url}"


@mcp.tool()
def add_comment(page_id: str, comment_text: str) -> str:
    """
    Add a comment to a Confluence page.

    Args:
        page_id:      Numeric page ID
        comment_text: Comment body (plain text or XHTML)
    """
    body = comment_text.strip()
    if not body.startswith("<"):
        body = f"<p>{body}</p>"

    payload = {
        "type": "comment",
        "container": {"id": page_id, "type": "page"},
        "body": {"storage": {"value": body, "representation": "storage"}},
    }
    try:
        with _client() as client:
            resp = client.post(
                f"{CONFLUENCE_URL}/rest/api/content",
                json=payload,
            )
            result = resp.json()
    except ConfluenceError as e:
        return f"ERROR: {e}"
    return f"Comment added (ID: {result['id']}) on page {page_id}"


@mcp.tool()
def add_label(page_id: str, labels: str) -> str:
    """
    Add labels to a Confluence page.

    Args:
        page_id: Numeric page ID
        labels:  Comma-separated label names (e.g. "gcp,slg,architecture")
    """
    label_list = [{"prefix": "global", "name": l.strip()} for l in labels.split(",") if l.strip()]
    try:
        with _client() as client:
            client.post(
                f"{CONFLUENCE_URL}/rest/api/content/{page_id}/label",
                json=label_list,
            )
    except ConfluenceError as e:
        return f"ERROR: {e}"
    names = ", ".join(l["name"] for l in label_list)
    return f"Added labels [{names}] to page {page_id}"


@mcp.tool()
def upload_attachment(
    page_id: str,
    file_name: str,
    file_content: str,
    media_type: str = "application/octet-stream",
    comment: str = "",
) -> str:
    """
    Upload a file attachment to a Confluence page.
    If a file with the same name already exists, it updates the existing attachment.

    Args:
        page_id:      Numeric page ID
        file_name:    Name for the file (e.g. "architecture.drawio", "report.csv")
        file_content: The file content as a string (for binary, use base64 and set media_type)
        media_type:   MIME type (e.g. "application/xml", "image/png")
        comment:      Optional comment for the attachment version
    """
    content_bytes = file_content.encode("utf-8")

    # Multipart upload needs its own headers — no Accept/Content-Type JSON
    # We reuse the same client but override headers inline via the files kwarg
    upload_headers = {
        "Authorization": f"Bearer {CONFLUENCE_PAT}",
        "X-Atlassian-Token": "nocheck",
    }

    import httpx as _httpx  # local import — only needed here
    try:
        with _httpx.Client(headers=upload_headers, verify=VERIFY_SSL,
                           timeout=_httpx.Timeout(total=60, connect=10),
                           trust_env=False) as upload_client:
            existing_resp = upload_client.get(
                f"{CONFLUENCE_URL}/rest/api/content/{page_id}/child/attachment",
                params={"filename": file_name},
            )
            if existing_resp.status_code >= 400:
                raise ConfluenceError(f"Could not check existing attachments: HTTP {existing_resp.status_code}")
            existing_atts = existing_resp.json().get("results", [])

            files = {"file": (file_name, content_bytes, media_type)}
            form_data = {"minorEdit": "true"}
            if comment:
                form_data["comment"] = comment

            if existing_atts:
                att_id = existing_atts[0]["id"]
                resp = upload_client.post(
                    f"{CONFLUENCE_URL}/rest/api/content/{page_id}/child/attachment/{att_id}/data",
                    files=files, data=form_data,
                )
            else:
                resp = upload_client.post(
                    f"{CONFLUENCE_URL}/rest/api/content/{page_id}/child/attachment",
                    files=files, data=form_data,
                )
            if resp.status_code >= 400:
                raise ConfluenceError(f"Upload failed: HTTP {resp.status_code}: {resp.text[:200]}")
            result = resp.json()
    except _httpx.TransportError as exc:
        return f"ERROR: Connection error during upload: {exc}"
    except ConfluenceError as e:
        return f"ERROR: {e}"

    if isinstance(result, dict) and "results" in result:
        result = result["results"][0]
    att_id = result.get("id", "?")
    dl = f"{CONFLUENCE_URL}{result.get('_links', {}).get('download', '')}"
    return f"Uploaded '{file_name}' to page {page_id} (attachment ID: {att_id})\nDownload: {dl}"
