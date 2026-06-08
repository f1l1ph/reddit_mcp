import os
from pathlib import Path
import httpx
import praw
from dotenv import load_dotenv

# Load .env from the repo root regardless of where the binary is invoked from
load_dotenv(Path(__file__).parent.parent.parent / ".env")


def get_mode() -> str:
    """'praw' if Reddit API credentials are present, 'json_api' otherwise."""
    if os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET"):
        return "praw"
    return "json_api"


def get_reddit() -> praw.Reddit:
    client_id = os.environ["REDDIT_CLIENT_ID"]
    client_secret = os.environ["REDDIT_CLIENT_SECRET"]
    username = os.environ.get("REDDIT_USERNAME")
    password = os.environ.get("REDDIT_PASSWORD")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "python:reddit-mcp:v0.1.0")

    if username and password:
        return praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent,
        )

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def get_http_client() -> httpx.Client:
    user_agent = os.environ.get("REDDIT_USER_AGENT", "python:reddit-mcp:v0.1.0")
    return httpx.Client(
        headers={"User-Agent": user_agent},
        timeout=30,
    )


def has_write_access() -> bool:
    return bool(os.environ.get("REDDIT_USERNAME") and os.environ.get("REDDIT_PASSWORD"))
