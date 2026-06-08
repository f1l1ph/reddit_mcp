# reddit-mcp

MCP server for Reddit. Gives any MCP-compatible AI agent read and write access to Reddit via the official API.

**Read tools** work with just a Reddit app (no account needed).  
**Write tools** (post, comment) require a Reddit account with 2FA disabled.

---

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A Reddit account to create an app

---

## 1. Create a Reddit app

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Scroll to the bottom and click **"create another app..."**
3. Fill in:
   - **Name:** anything (e.g. `my-reddit-mcp`)
   - **Type:** select **script**
   - **Redirect URI:** `http://localhost:8080` (not used, but required)
4. Click **Create app**
5. Note the **client ID** (under the app name) and the **secret**

---

## 2. Set up credentials

```bash
cp .env.example .env
```

Edit `.env`:

```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret

# Only needed for write tools (post, comment). Leave blank for read-only.
# 2FA must be OFF on this account.
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
```

---

## 3. Install

```bash
uv pip install -e .
# or: pip install -e .
```

---

## 4. Configure your AI tool

### Claude Code

Add to `~/.claude/settings.json` (global) or `.claude/settings.json` (project-level):

```json
{
  "mcpServers": {
    "reddit": {
      "command": "reddit-mcp",
      "cwd": "/path/to/reddit_mcp"
    }
  }
}
```

If you installed with uv into a virtual environment:

```json
{
  "mcpServers": {
    "reddit": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/reddit_mcp", "reddit-mcp"]
    }
  }
}
```

### Qwen Code

Add to `~/.qwen/settings.json`:

```json
{
  "mcpServers": {
    "reddit": {
      "command": "reddit-mcp",
      "cwd": "/path/to/reddit_mcp"
    }
  }
}
```

With uv:

```json
{
  "mcpServers": {
    "reddit": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/reddit_mcp", "reddit-mcp"]
    }
  }
}
```

---

## Available tools

| Tool                 | Auth  | Description                                                            |
| -------------------- | ----- | ---------------------------------------------------------------------- |
| `scrape_subreddit`   | read  | Fetch posts from a subreddit. Paginates up to 1000. Optional comments. |
| `search_reddit`      | read  | Search across Reddit or specific subreddits by keyword.                |
| `get_post`           | read  | Get a single post and its comments by ID or URL.                       |
| `get_subreddit_info` | read  | Subscriber count, description, rules.                                  |
| `submit_post`        | write | Submit a text or link post.                                            |
| `submit_comment`     | write | Post a top-level comment on a post.                                    |
| `reply_to_comment`   | write | Reply to an existing comment.                                          |
| `get_my_karma`       | write | Karma breakdown by subreddit.                                          |
| `get_my_posts`       | write | Recent post history for your account.                                  |
| `get_my_comments`    | write | Recent comment history for your account.                               |

Write tools only appear if `REDDIT_USERNAME` and `REDDIT_PASSWORD` are set.

---

## Multi-account setup

Run one server instance per account with a separate `.env` file:

```bash
# Terminal 1 — account A
REDDIT_USERNAME=account_a REDDIT_PASSWORD=... reddit-mcp

# Terminal 2 — account B
REDDIT_USERNAME=account_b REDDIT_PASSWORD=... reddit-mcp
```

Or point each config entry at a different directory, each with its own `.env`.

---

## Rate limits

Reddit allows 100 API requests per minute with OAuth. PRAW handles this automatically — it sleeps as needed. No manual throttling required.

---

## License

MIT
