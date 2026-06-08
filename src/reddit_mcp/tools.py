import json
import time
import httpx
import praw
import praw.models

_BASE = "https://www.reddit.com"


# ---------------------------------------------------------------------------
# JSON API helpers (no credentials required)
# ---------------------------------------------------------------------------

def _extract_post_id(post_id_or_url: str) -> str:
    if post_id_or_url.startswith("http"):
        parts = post_id_or_url.rstrip("/").split("/")
        try:
            return parts[parts.index("comments") + 1]
        except (ValueError, IndexError):
            raise ValueError(f"Cannot extract post ID from URL: {post_id_or_url}")
    return post_id_or_url


def _post_from_json(d: dict) -> dict:
    return {
        "id": d.get("id", ""),
        "title": d.get("title", ""),
        "body": d.get("selftext", ""),
        "score": d.get("score", 0),
        "url": d.get("url", ""),
        "permalink": f"https://reddit.com{d.get('permalink', '')}",
        "created_utc": int(d.get("created_utc", 0)),
        "num_comments": d.get("num_comments", 0),
        "author": d.get("author") or "[deleted]",
        "subreddit": d.get("subreddit", ""),
    }


def _comment_from_json(d: dict) -> dict:
    return {
        "id": d.get("id", ""),
        "body": d.get("body", ""),
        "score": d.get("score", 0),
        "author": d.get("author") or "[deleted]",
        "created_utc": int(d.get("created_utc", 0)),
    }


def _fetch_listing(client: httpx.Client, url: str, params: dict, limit: int) -> list[dict]:
    posts: list[dict] = []
    after: str | None = None
    while len(posts) < limit:
        batch = min(100, limit - len(posts))
        p = {**params, "limit": batch, "raw_json": 1}
        if after:
            p["after"] = after
        r = client.get(url, params=p)
        r.raise_for_status()
        data = r.json()["data"]
        children = data.get("children", [])
        if not children:
            break
        posts.extend(c["data"] for c in children if c.get("kind") == "t3")
        after = data.get("after")
        if not after or len(children) < batch:
            break
        time.sleep(2)  # stay well under the 10 req/min unauthenticated limit
    return posts[:limit]


def scrape_subreddit_json(
    client: httpx.Client,
    subreddit: str,
    query: str | None,
    limit: int,
    sort: str,
    time_filter: str,
    include_comments: bool,
    comment_limit: int,
) -> str:
    limit = min(limit, 1000)
    if query:
        url = f"{_BASE}/r/{subreddit}/search.json"
        params: dict = {"q": query, "restrict_sr": 1, "sort": sort, "t": time_filter}
    else:
        url = f"{_BASE}/r/{subreddit}/{sort}.json"
        params = {"t": time_filter} if sort in ("top", "controversial") else {}

    raw_posts = _fetch_listing(client, url, params, limit)
    posts = [_post_from_json(p) for p in raw_posts]

    if include_comments:
        for post in posts:
            try:
                post["comments"] = _get_comments_json(client, post["id"], comment_limit)
                time.sleep(1)
            except Exception:
                post["comments"] = []

    return json.dumps(posts)


def search_reddit_json(
    client: httpx.Client,
    query: str,
    subreddits: list[str] | None,
    limit: int,
    sort: str,
    time_filter: str,
) -> str:
    if subreddits:
        url = f"{_BASE}/r/{'+'.join(subreddits)}/search.json"
        params: dict = {"q": query, "restrict_sr": 1, "sort": sort, "t": time_filter}
    else:
        url = f"{_BASE}/search.json"
        params = {"q": query, "sort": sort, "t": time_filter}

    raw_posts = _fetch_listing(client, url, params, min(limit, 1000))
    return json.dumps([_post_from_json(p) for p in raw_posts])


def _get_comments_json(client: httpx.Client, post_id: str, comment_limit: int) -> list[dict]:
    r = client.get(f"{_BASE}/comments/{post_id}.json", params={"limit": comment_limit, "raw_json": 1})
    r.raise_for_status()
    result = r.json()
    comments_listing = result[1]["data"]["children"]
    return [
        _comment_from_json(c["data"])
        for c in comments_listing
        if c.get("kind") == "t1"
    ][:comment_limit]


def get_post_json(client: httpx.Client, post_id: str, comment_limit: int) -> str:
    pid = _extract_post_id(post_id)
    r = client.get(f"{_BASE}/comments/{pid}.json", params={"limit": comment_limit, "raw_json": 1})
    r.raise_for_status()
    result = r.json()
    post = _post_from_json(result[0]["data"]["children"][0]["data"])
    post["comments"] = [
        _comment_from_json(c["data"])
        for c in result[1]["data"]["children"]
        if c.get("kind") == "t1"
    ][:comment_limit]
    return json.dumps(post)


def get_subreddit_info_json(client: httpx.Client, subreddit: str) -> str:
    r = client.get(f"{_BASE}/r/{subreddit}/about.json", params={"raw_json": 1})
    r.raise_for_status()
    d = r.json()["data"]
    return json.dumps({
        "name": d.get("display_name", ""),
        "title": d.get("title", ""),
        "description": d.get("public_description", ""),
        "subscribers": d.get("subscribers", 0),
        "active_users": d.get("active_user_count", 0),
        "over18": d.get("over18", False),
        "rules": [],  # rules endpoint requires auth
    })


def _post_to_dict(submission: praw.models.Submission, include_comments: bool = False, comment_limit: int = 20) -> dict:
    data = {
        "id": submission.id,
        "title": submission.title,
        "body": submission.selftext,
        "score": submission.score,
        "url": submission.url,
        "permalink": f"https://reddit.com{submission.permalink}",
        "created_utc": int(submission.created_utc),
        "num_comments": submission.num_comments,
        "author": str(submission.author) if submission.author else "[deleted]",
        "subreddit": submission.subreddit.display_name,
    }
    if include_comments:
        submission.comments.replace_more(limit=0)
        data["comments"] = [
            _comment_to_dict(c)
            for c in list(submission.comments.list())[:comment_limit]
            if isinstance(c, praw.models.Comment)
        ]
    return data


def _comment_to_dict(comment: praw.models.Comment) -> dict:
    return {
        "id": comment.id,
        "body": comment.body,
        "score": comment.score,
        "author": str(comment.author) if comment.author else "[deleted]",
        "created_utc": int(comment.created_utc),
    }


def scrape_subreddit(
    reddit: praw.Reddit,
    subreddit: str,
    query: str | None,
    limit: int,
    sort: str,
    time_filter: str,
    include_comments: bool,
    comment_limit: int,
) -> str:
    sub = reddit.subreddit(subreddit)
    limit = min(limit, 1000)

    if query:
        posts = sub.search(query, sort=sort, time_filter=time_filter, limit=limit)
    elif sort == "top":
        posts = sub.top(time_filter=time_filter, limit=limit)
    elif sort == "controversial":
        posts = sub.controversial(time_filter=time_filter, limit=limit)
    elif sort == "new":
        posts = sub.new(limit=limit)
    elif sort == "rising":
        posts = sub.rising(limit=limit)
    else:
        posts = sub.hot(limit=limit)

    return json.dumps([_post_to_dict(p, include_comments, comment_limit) for p in posts])


def search_reddit(
    reddit: praw.Reddit,
    query: str,
    subreddits: list[str] | None,
    limit: int,
    sort: str,
    time_filter: str,
) -> str:
    target = reddit.subreddit("+".join(subreddits)) if subreddits else reddit.subreddit("all")
    posts = target.search(query, sort=sort, time_filter=time_filter, limit=min(limit, 1000))
    return json.dumps([_post_to_dict(p) for p in posts])


def get_post(reddit: praw.Reddit, post_id: str, comment_limit: int) -> str:
    if post_id.startswith("http"):
        submission = reddit.submission(url=post_id)
    else:
        submission = reddit.submission(id=post_id)

    submission.comments.replace_more(limit=0)
    data = _post_to_dict(submission)
    data["comments"] = [
        _comment_to_dict(c)
        for c in list(submission.comments.list())[:comment_limit]
        if isinstance(c, praw.models.Comment)
    ]
    return json.dumps(data)


def get_subreddit_info(reddit: praw.Reddit, subreddit: str) -> str:
    sub = reddit.subreddit(subreddit)
    rules = []
    try:
        rules = [{"short_name": r.short_name, "description": r.description} for r in sub.rules]
    except Exception:
        pass

    return json.dumps({
        "name": sub.display_name,
        "title": sub.title,
        "description": sub.public_description,
        "subscribers": sub.subscribers,
        "active_users": sub.active_user_count,
        "over18": sub.over18,
        "rules": rules,
    })


def submit_post(reddit: praw.Reddit, subreddit: str, title: str, body: str | None, url: str | None) -> str:
    sub = reddit.subreddit(subreddit)
    if url:
        submission = sub.submit(title, url=url)
    else:
        submission = sub.submit(title, selftext=body or "")
    return json.dumps({"id": submission.id, "permalink": f"https://reddit.com{submission.permalink}"})


def submit_comment(reddit: praw.Reddit, post_id: str, body: str) -> str:
    submission = reddit.submission(id=post_id)
    comment = submission.reply(body)
    return json.dumps({"id": comment.id, "permalink": f"https://reddit.com{comment.permalink}"})


def reply_to_comment(reddit: praw.Reddit, comment_id: str, body: str) -> str:
    comment = reddit.comment(id=comment_id)
    reply = comment.reply(body)
    return json.dumps({"id": reply.id, "permalink": f"https://reddit.com{reply.permalink}"})


def get_my_karma(reddit: praw.Reddit) -> str:
    breakdown = reddit.user.karma()
    return json.dumps({
        str(sub): {"comment_karma": karma["comment_karma"], "link_karma": karma["link_karma"]}
        for sub, karma in breakdown.items()
    })


def get_my_posts(reddit: praw.Reddit, limit: int) -> str:
    posts = reddit.user.me().submissions.new(limit=limit)
    return json.dumps([_post_to_dict(p) for p in posts])


def get_my_comments(reddit: praw.Reddit, limit: int) -> str:
    comments = reddit.user.me().comments.new(limit=limit)
    return json.dumps([_comment_to_dict(c) for c in comments])
