# Confluence MCP Server

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![MCP v1.0](https://img.shields.io/badge/MCP-v1.0-green)
![Tools](https://img.shields.io/badge/tools-20-orange)
![License: MIT](https://img.shields.io/badge/license-MIT-yellow)

Model Context Protocol (MCP) server that gives **GitHub Copilot** full read/write access to your **Confluence** instance (Cloud, Server, or Data Center).

> Works with any Confluence instance — Atlassian Cloud (`*.atlassian.net`), self-hosted Server, or Data Center.

---

## Configuration

You need two things before running setup:

| Variable         | What to set                          | Example                                                               |
| ---------------- | ------------------------------------ | --------------------------------------------------------------------- |
| `CONFLUENCE_URL` | Base URL of your Confluence instance | `https://yourcompany.atlassian.net` or `https://wiki.yourcompany.com` |
| `CONFLUENCE_PAT` | Your Personal Access Token           | (generated in step 1 below)                                           |

`setup.ps1` will prompt you for both interactively. You can also pass them as arguments:

```powershell
.\setup.ps1 -Url "https://yourcompany.atlassian.net" -Pat "YOUR_TOKEN"
```

---

## Quick Start

### 1. Create a Personal Access Token

In your Confluence, go to **Profile → Personal Access Tokens** and create a new token.

- **Atlassian Cloud:** `https://yourcompany.atlassian.net` → Profile → Security → API tokens
- **Server / Data Center:** `https://your-confluence/plugins/personalaccesstokens/usertokens.action`

### 2. Run Setup

```powershell
cd confluence-mcp
.\setup.ps1
```

The script will:

- Prompt for your **Confluence URL** and **PAT** (or pass via `-Url` / `-Pat` flags)
- Create a Python virtual environment
- Install dependencies (`mcp`, `httpx`)
- Validate your credentials against your Confluence instance
- Auto-write the MCP config into VS Code

### 3. Add to VS Code

Open **Settings JSON** (`Ctrl+Shift+P` → `Preferences: Open User Settings (JSON)`) and add the MCP server config printed by the setup script:

```json
{
  "mcp": {
    "servers": {
      "confluence": {
        "command": "C:\\path\\to\\.venv\\Scripts\\python.exe",
        "args": ["C:\\path\\to\\server.py"],
        "env": {
          "CONFLUENCE_URL": "https://your-confluence.company.com",
          "CONFLUENCE_PAT": "YOUR_TOKEN_HERE"
        }
      }
    }
  }
}
```

### 4. Verify

`Ctrl+Shift+P` → **MCP: List Servers** → you should see `confluence` with a green status.

---

## Available Tools

### Read Tools (6)

| Tool                | Description         | Example                                        |
| ------------------- | ------------------- | ---------------------------------------------- |
| `get_page`          | Fetch page by ID    | `get_page("504270225")`                        |
| `search_confluence` | CQL search          | `search_confluence('text ~ "SLG"')`            |
| `get_page_by_title` | Find by exact title | `get_page_by_title("SAP", "SLG Architecture")` |
| `get_space_pages`   | List space pages    | `get_space_pages("SAP")`                       |
| `get_page_children` | Navigate hierarchy  | `get_page_children("479570414")`               |
| `get_page_comments` | Read comments       | `get_page_comments("504270225")`               |

### Write Tools (6)

| Tool              | Description                 | Example                                          |
| ----------------- | --------------------------- | ------------------------------------------------ |
| `prepend_to_page` | Add content to the top      | `prepend_to_page("685316626", "Note")`           |
| `append_to_page`  | Add content to the bottom   | `append_to_page("685316626", "Footer")`          |
| `update_page`     | Replace entire page content | `update_page("504270225", "<p>New content</p>")` |
| `create_page`     | Create new page             | `create_page("SAP", "My Page", "<p>Hello</p>")`  |
| `add_comment`     | Comment on a page           | `add_comment("504270225", "Reviewed")`           |
| `add_label`       | Add labels                  | `add_label("504270225", "gcp,prod")`             |

### Crawl & Navigation Tools (2)

| Tool            | Description                          | Example                                        |
| --------------- | ------------------------------------ | ---------------------------------------------- |
| `crawl_pages`   | Smart search + follow links/children | `crawl_pages("architecture", space_key="SAP")` |
| `get_page_tree` | Show page hierarchy tree             | `get_page_tree("479570414", depth=3)`          |

### Attachment Tools (2)

| Tool                | Description                   | Example                                                  |
| ------------------- | ----------------------------- | -------------------------------------------------------- |
| `get_attachments`   | List files attached to a page | `get_attachments("504270225")`                           |
| `upload_attachment` | Upload a file to a page       | `upload_attachment("504270225", "data.csv", "a,b\n1,2")` |

### Diagram Tools (4)

| Tool                     | Description                                    | Example                     |
| ------------------------ | ---------------------------------------------- | --------------------------- |
| `list_diagram_icons`     | Browse GCP/SAP/Azure icon catalog (225+ icons) | `list_diagram_icons("gcp")` |
| `preview_drawio_diagram` | Generate local .drawio file for review         | See below                   |
| `publish_drawio_diagram` | Generate and upload diagram to Confluence page | See below                   |
| `create_drawio_diagram`  | Legacy: create + upload in one step            | See below                   |

> **Diagram features:** Topology-aware layout, orthogonal edge routing with collision avoidance, embedded GCP legacy blue icons (225), SAP BTP and Azure support. No generic shapes.

---

## Usage Examples in Copilot Chat

```
@workspace Search Confluence for architecture docs
@workspace Read the page with ID 504270225
@workspace Crawl across the SAP space and find everything about GCP migration
@workspace Show me the page tree under page ID 479570414
@workspace Create a GCP architecture diagram for our data pipeline on page 504270225
@workspace List the available GCP icons for diagrams
@workspace Upload the CSV report to page 685316626
@workspace Create a new child page under page 479570414
```

---

## CQL Quick Reference

Confluence Query Language (CQL) powers the `search_confluence` tool:

```sql
-- Full-text search
text ~ "submission letter"

-- Pages in a specific space
space = "SAP" AND type = "page"

-- Recently modified
lastModified > "2025-06-01" AND space = "SAP"

-- By creator
creator = currentUser()

-- By label
label = "gcp" AND label = "slg"

-- Title match
title ~ "Architecture"
```

---

## Project Structure

```
confluence-mcp/
├── server.py          # MCP server (20 tools)
├── icon_data.py       # 225 GCP legacy blue icons (base64 PNG)
├── setup.ps1          # One-click setup script
├── requirements.txt   # Python dependencies
├── docs/index.html    # Documentation site
└── README.md          # This file
```

## Requirements

- Python 3.10+
- VS Code with GitHub Copilot Chat
- A Confluence Personal Access Token (create one in your Confluence profile settings)

---

## Troubleshooting

**Server not showing in MCP: List Servers?**

1. `Ctrl+Shift+P` → **MCP: Reset All Cached MCP Servers**
2. Reload VS Code (`Ctrl+Shift+P` → **Developer: Reload Window**)
3. Check that the Python path in your config points to the `.venv` Python executable

**Connection errors?**

- Ensure you're on the correct network (VPN if needed for self-hosted Confluence)
- Verify your PAT hasn't expired (check your Confluence profile → Personal Access Tokens)

**SSL errors?**

- The server uses `verify=False` for corporate proxy/SSL inspection — this is expected behavior

---

_Open source — contributions welcome_
