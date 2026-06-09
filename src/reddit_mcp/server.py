from mcp.server.fastmcp import FastMCP
from pathlib import Path
from .client import get_mode, get_reddit, get_http_client, get_oauth_client, has_write_access
from . import tools

mcp = FastMCP("reddit-mcp")

_mode = get_mode()
_reddit = get_reddit() if _mode == "praw" else None
_oauth = get_oauth_client()  # None if no session.json or no token_v2
_http = get_http_client() if (_mode == "json_api" and _oauth is None) else None
_write = has_write_access()
_session_exists = (Path(__file__).parent.parent.parent / "session.json").exists()


@mcp.tool()
def scrape_subreddit(
    subreddit: str,
    limit: int = 100,
    sort: str = "hot",
    time_filter: str = "week",
    include_comments: bool = False,
    comment_limit: int = 20,
    query: str | None = None,
) -> str:
    """Fetch posts from a subreddit. Paginates internally up to `limit` (max 1000).
    sort: hot | new | top | rising | controversial
    time_filter: hour | day | week | month | year | all (used with top/controversial or when query is set)
    Set include_comments=True to fetch up to comment_limit comments per post."""
    if _mode == "praw":
        return tools.scrape_subreddit(_reddit, subreddit, query, limit, sort, time_filter, include_comments, comment_limit)
    if _oauth is not None:
        return tools.scrape_subreddit_oauth(_oauth, subreddit, query, limit, sort, time_filter)
    return tools.scrape_subreddit_json(_http, subreddit, query, limit, sort, time_filter, include_comments, comment_limit)


@mcp.tool()
def search_reddit(
    query: str,
    subreddits: list[str] | None = None,
    limit: int = 50,
    sort: str = "relevance",
    time_filter: str = "year",
) -> str:
    """Search Reddit for posts matching a keyword query.
    subreddits: list of subreddit names to search within, or None to search all of Reddit.
    sort: relevance | hot | top | new | comments
    time_filter: hour | day | week | month | year | all"""
    if _mode == "praw":
        return tools.search_reddit(_reddit, query, subreddits, limit, sort, time_filter)
    if _oauth is not None:
        return tools.search_reddit_oauth(_oauth, query, subreddits, limit, sort, time_filter)
    return tools.search_reddit_json(_http, query, subreddits, limit, sort, time_filter)


@mcp.tool()
def get_post(post_id: str, comment_limit: int = 100) -> str:
    """Get a single post and its comments. post_id can be a Reddit post ID (e.g. 'abc123') or a full URL."""
    if _mode == "praw":
        return tools.get_post(_reddit, post_id, comment_limit)
    return tools.get_post_json(_http, post_id, comment_limit)


@mcp.tool()
def get_subreddit_info(subreddit: str) -> str:
    """Get metadata for a subreddit: subscriber count, description, active users, and rules."""
    if _mode == "praw":
        return tools.get_subreddit_info(_reddit, subreddit)
    return tools.get_subreddit_info_json(_http, subreddit)


if _write:
    @mcp.tool()
    def submit_post(subreddit: str, title: str, body: str | None = None, url: str | None = None) -> str:
        """Submit a new post to a subreddit. Provide body for a text post or url for a link post."""
        return tools.submit_post(_reddit, subreddit, title, body, url)

    @mcp.tool()
    def submit_comment(post_id: str, body: str) -> str:
        """Post a top-level comment on a Reddit post. post_id is the post's ID (not a URL)."""
        return tools.submit_comment(_reddit, post_id, body)

    @mcp.tool()
    def reply_to_comment(comment_id: str, body: str) -> str:
        """Reply to an existing comment. comment_id is the comment's ID."""
        return tools.reply_to_comment(_reddit, comment_id, body)

    @mcp.tool()
    def get_my_karma() -> str:
        """Get karma breakdown by subreddit for the authenticated account."""
        return tools.get_my_karma(_reddit)

    @mcp.tool()
    def get_my_posts(limit: int = 25) -> str:
        """Get recent posts by the authenticated account."""
        return tools.get_my_posts(_reddit, limit)

    @mcp.tool()
    def get_my_comments(limit: int = 25) -> str:
        """Get recent comments by the authenticated account."""
        return tools.get_my_comments(_reddit, limit)


if _session_exists:
    @mcp.tool()
    async def pw_submit_comment(post_url: str, comment_text: str) -> str:
        """Post a comment on a Reddit post using browser automation. post_url is the full URL."""
        import json
        import asyncio
        from .playwright_client import submit_comment as _submit
        return json.dumps(await asyncio.to_thread(_submit, post_url, comment_text))

    @mcp.tool()
    async def pw_check_session() -> str:
        """Check whether the saved Reddit browser session is still valid."""
        import json
        import asyncio
        from .playwright_client import check_session_valid
        return json.dumps({"valid": await asyncio.to_thread(check_session_valid)})


def main() -> None:
    mcp.run()
