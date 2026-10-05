#!/usr/bin/env python3
"""Free, source-led image publishing pipeline for Instagram."""

from __future__ import annotations

import base64
import email.utils
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont
from nacl.public import PublicKey, SealedBox

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
POSTS = DOCS / "posts"
IST = ZoneInfo("Asia/Kolkata")
WIDTH, HEIGHT = 1080, 1350
MAX_CAROUSEL_SLIDES = 5
INSTAGRAM_CAPTION_LIMIT = 2200
BG, PAPER, MUTED, ACCENT, GRID = "#10120F", "#F4F5EF", "#B7B9B0", "#D7FF64", "#22251F"
USER_AGENT = "AIBriefPublisher/1.0 (RSS-based editorial card)"


class TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def strip_markup(value: str) -> str:
    parser = TextOnly()
    parser.feed(value or "")
    text = html.unescape(" ".join(parser.parts))
    text = re.sub(r"https?://\S+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def child_text(element: ET.Element, names: tuple[str, ...]) -> str:
    for child in element.iter():
        if child is element:
            continue
        if child.tag.split("}")[-1].lower() in names and child.text and child.text.strip():
            return child.text.strip()
    return ""


def entry_link(entry: ET.Element) -> str:
    for child in list(entry):
        if child.tag.split("}")[-1].lower() == "link":
            link = child.attrib.get("href", "").strip()
            if link:
                return link
            if child.text and child.text.strip():
                return child.text.strip()
    return ""


def entry_date(entry: ET.Element) -> datetime | None:
    raw = child_text(entry, ("published", "pubdate", "updated", "date"))
    if not raw:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


def fetch_xml(url: str) -> ET.Element:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return ET.fromstring(response.read())


def candidates(now: datetime) -> list[dict]:
    sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    found = []
    for source in sources:
        try:
            feed = fetch_xml(source["feed"])
        except Exception as exc:
            print(f"Feed unavailable: {source['name']} ({type(exc).__name__})", file=sys.stderr)
            continue
        for entry in feed.iter():
            if entry.tag.split("}")[-1].lower() not in {"item", "entry"}:
                continue
            title = strip_markup(child_text(entry, ("title",)))
            link = entry_link(entry)
            published = entry_date(entry)
            if not title or not link or not published:
                continue
            age = now - published
            if age < timedelta(minutes=-10) or age > timedelta(days=3):
                continue
            summary = strip_markup(child_text(entry, ("description", "summary", "content")))
            found.append({
                "title": title,
                "url": link,
                "published": published.isoformat(),
                "source": source["name"],
                "priority": int(source.get("priority", 9)),
                "summary": summary,
            })
    return found


def choose_stories(now: datetime, limit: int = MAX_CAROUSEL_SLIDES) -> list[dict]:
    seen = read_json(DOCS / "seen.json", [])
    seen_urls = {item.get("url") for item in seen if isinstance(item, dict)}
    fresh = [item for item in candidates(now) if item["url"] not in seen_urls]
    if not fresh:
        return []
    # Newest items win; primary-source priority breaks timestamp ties.
    fresh.sort(key=lambda item: (datetime.fromisoformat(item["published"]), -item["priority"]), reverse=True)
    return fresh[:limit]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    suffix = "-Bold" if bold else ""
    for path in (
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffix}.ttf",
        f"/usr/share/fonts/truetype/liberation2/LiberationSans{suffix}.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, use_font: ImageFont.FreeTypeFont, width: int, max_lines: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=use_font)[2] <= width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    full_text = " ".join(words)
    if lines and " ".join(lines) != full_text:
        last = lines[-1]
        while last and draw.textbbox((0, 0), last + "…", font=use_font)[2] > width:
            last = last[:-1].rstrip()
        lines[-1] = last + "…"
    return lines


def draw_card(story: dict, output: Path, issued: date, slide_number: int, total_slides: int) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    for x in range(0, WIDTH, 48):
        draw.line((x, 0, x, HEIGHT), fill=GRID, width=1)
    for y in range(0, HEIGHT, 48):
        draw.line((0, y, WIDTH, y), fill=GRID, width=1)

    # An original, minimalist orbital motif built from vector primitives.
    draw.ellipse((745, -90, 1120, 285), outline="#414A2A", width=2)
    draw.ellipse((800, -35, 1065, 230), outline="#303B24", width=2)
    draw.ellipse((870, 35, 995, 160), fill="#202719", outline="#576338", width=2)
    draw.ellipse((922, 87, 943, 108), fill=ACCENT)
    draw.line((780, 97, 1075, 97), fill="#343E25", width=2)
    draw.line((932, -48, 932, 245), fill="#343E25", width=2)

    draw.text((80, 62), "AI BRIEF", font=load_font(28, True), fill=ACCENT)
    draw.text((80, 109), "THE DAILY SIGNAL", font=load_font(17), fill="#A6AA9E")
    draw.rounded_rectangle((80, 160, 272, 204), radius=22, fill=ACCENT)
    badge = "AI EXPLAINER" if story.get("kind") == "evergreen" else "STORY"
    draw.text((101, 170), f"{badge} {slide_number:02d} / {total_slides:02d}", font=load_font(15, True), fill=BG)

    title_font = load_font(70, True)
    lines = wrap_text(draw, story["title"], title_font, 900, 4)
    while max((draw.textbbox((0, 0), line, font=title_font)[2] for line in lines), default=0) > 920 and title_font.size > 54:
        title_font = load_font(title_font.size - 4, True)
        lines = wrap_text(draw, story["title"], title_font, 900, 4)
    y = 330
    for line in lines:
        draw.text((80, y), line, font=title_font, fill=PAPER)
        y += title_font.size + 16
    y += 22
    draw.rounded_rectangle((80, y, 164, y + 6), radius=3, fill=ACCENT)
    y += 44

    summary = story.get("summary") or f"A new update from {story['source']}. Read the source for the full details."
    summary_font = load_font(27)
    for line in wrap_text(draw, summary, summary_font, 900, 3):
        draw.text((80, y), line, font=summary_font, fill=MUTED)
        y += 42

    panel_y = 930
    draw.rounded_rectangle((80, panel_y, 1000, panel_y + 158), radius=18, fill="#1B1E19", outline="#30342C", width=1)
    draw.text((112, panel_y + 28), "WHY IT MATTERS", font=load_font(16, True), fill=ACCENT)
    panel_copy = (
        f"Evergreen explainer based on {story['source']}. The source is in the caption."
        if story.get("kind") == "evergreen"
        else f"{story['source']} published this update. The source is in the caption."
    )
    for index, line in enumerate(wrap_text(draw, panel_copy, load_font(23), 850, 2)):
        draw.text((112, panel_y + 76 + index * 34), line, font=load_font(23), fill=PAPER)

    draw.line((80, 1200, 1000, 1200), fill="#44463E", width=1)
    draw.text((80, 1232), f"SOURCE  /  {story['source'].upper()[:55]}", font=load_font(16), fill="#A6AA9E")
    draw.text((80, 1282), f"AI BRIEF  ·  {issued.strftime('%d %b %Y').upper()}", font=load_font(16), fill="#72766D")
    draw.text((1000, 1282), "01 / 01", font=load_font(16), fill=ACCENT, anchor="ra")

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="JPEG", quality=92, optimize=True, progressive=True)


def short_text(value: str, limit: int) -> str:
    clean = re.sub(r"\s+", " ", value or "").strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def caption_for(stories: list[dict]) -> str:
    evergreen = bool(stories) and all(story.get("kind") == "evergreen" for story in stories)
    if evergreen:
        lines = ["Today's AI Brief: an evergreen AI explainer.", "No new eligible stories were available today; this post is clearly labeled as background reading."]
    elif len(stories) == 1:
        lines = ["Today's AI Brief: one new development."]
    else:
        lines = [f"Today's AI Brief: {len(stories)} developments.", "Swipe through for the stories and sources."]
    for index, story in enumerate(stories, start=1):
        title = short_text(story["title"], 130)
        source = short_text(story["source"], 60)
        url = story["url"]
        summary = short_text(story.get("summary", ""), 110)
        entry = f"{index}. {title}"
        if summary:
            entry += f"\n{summary}"
        entry += f"\nSource: {source}\n{url}"
        footer = "AI Brief · Evergreen AI explainer" if evergreen else "AI Brief · Daily AI developments"
        candidate = "\n\n".join(lines + [entry, footer])
        if len(candidate) > INSTAGRAM_CAPTION_LIMIT:
            entry = f"{index}. {title}\nSource: {source}\n{url}"
            candidate = "\n\n".join(lines + [entry, footer])
        if len(candidate) <= INSTAGRAM_CAPTION_LIMIT:
            lines.append(entry)
    lines.append("AI Brief · Evergreen AI explainer" if evergreen else "AI Brief · Daily AI developments")
    caption = "\n\n".join(lines)
    if len(caption) > INSTAGRAM_CAPTION_LIMIT:
        raise RuntimeError("The source links exceed Instagram's caption limit.")
    return caption


EVERGREEN_EXPLAINERS = [
    {"title": "What is a context window?", "summary": "A context window is the text and other input a model can consider in one request. Longer context can help with large documents, but useful answers still depend on relevance and clear instructions.", "source": "Anthropic Docs", "url": "https://docs.anthropic.com/en/docs/build-with-claude/context-windows"},
    {"title": "What are AI model evaluations?", "summary": "Evaluations use representative tasks and scoring criteria to measure how a model behaves. They help teams compare changes and catch regressions before release.", "source": "OpenAI Platform Docs", "url": "https://platform.openai.com/docs/guides/evals"},
    {"title": "How does retrieval-augmented generation work?", "summary": "RAG retrieves relevant material at answer time and gives it to a model as context. This can ground responses in a chosen knowledge base, though retrieval quality still matters.", "source": "Google Cloud Docs", "url": "https://cloud.google.com/use-cases/retrieval-augmented-generation"},
    {"title": "What is a token in an AI model?", "summary": "Models process text as tokens: pieces that may be whole words, word fragments, or punctuation. Token counts affect context limits and how much text a request can include.", "source": "OpenAI Help Center", "url": "https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them"},
    {"title": "Why do AI models hallucinate?", "summary": "A fluent answer is not proof that a claim is true. Models can produce unsupported details, so important claims should be checked against reliable sources.", "source": "OpenAI Research", "url": "https://openai.com/index/why-language-models-hallucinate/"},
    {"title": "What is an AI agent?", "summary": "An AI agent combines a model with instructions and tools to take steps toward a goal. Clear boundaries and checks matter when tools can change external systems.", "source": "OpenAI Platform Docs", "url": "https://platform.openai.com/docs/guides/agents"},
    {"title": "What does multimodal AI mean?", "summary": "A multimodal model can work with more than one kind of input or output, such as text, images, audio, or video. The supported capabilities vary by model.", "source": "Google AI for Developers", "url": "https://ai.google.dev/gemini-api/docs"},
];

def write_index() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    page = "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>AI Brief</title><body style=\"background:#10120f;color:#f4f5ef;font:16px system-ui;max-width:760px;margin:4rem auto;padding:0 1rem\"><h1>AI Brief</h1><p>Daily AI developments with links to primary sources.</p><a href=\"current.json\" style=\"color:#d7ff64\">Today's publish package</a><h2>Recent image cards</h2><ul>"
    for image in sorted(POSTS.glob("*.jpg"), reverse=True)[:30]:
        page += f'<li><a style="color:#d7ff64" href="posts/{image.name}">{image.stem}</a></li>'
    page += "</ul></body></html>\n"
    (DOCS / "index.html").write_text(page, encoding="utf-8")


def evergreen_story(today: date) -> dict:
    # Rotate through sourced, non-news explainers so a slow news day still gets a useful post.
    item = EVERGREEN_EXPLAINERS[today.toordinal() % len(EVERGREEN_EXPLAINERS)]
    return {**item, "published": datetime.now(timezone.utc).isoformat(), "priority": 0, "kind": "evergreen"}


def prepare() -> None:
    now = datetime.now(timezone.utc)
    today = now.astimezone(IST).date()
    stories = choose_stories(now)
    if len(stories) == 1:
        stories[0]["kind"] = "news"
    elif not stories:
        stories = [evergreen_story(today)]

    package = {"date": today.isoformat(), "status": "ready", "generated_at": now.isoformat()}
    owner, repo = os.environ["GITHUB_REPOSITORY"].split("/", 1)
    image_paths = []
    image_urls = []
    alt_texts = []
    for index, story in enumerate(stories, start=1):
        filename = f"{today.isoformat()}-{index:02d}.jpg"
        image_path = POSTS / filename
        draw_card(story, image_path, today, index, len(stories))
        image_paths.append(f"posts/{filename}")
        image_urls.append(f"https://{owner}.github.io/{repo}/posts/{filename}")
        alt_texts.append(short_text(
            f"AI Brief {'evergreen explainer' if story.get('kind') == 'evergreen' else 'news'} image. Headline: {story['title']}. Source: {story['source']}.",
            1000,
        ))

    package.update({
        "stories": stories,
        "story": stories[0],
        "caption": caption_for(stories),
        "alt_texts": alt_texts,
        "image_paths": image_paths,
        "image_urls": image_urls,
        "carousel": len(stories) > 1,
        "content_type": "evergreen" if stories[0].get("kind") == "evergreen" else "news",
    })
    print(f"Prepared today's {package['content_type']} image." if len(stories) == 1 else f"Prepared {len(stories)}-image news carousel.")
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "current.json").write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_index()


def request_json(url: str, data: dict | None = None, method: str | None = None, headers: dict | None = None) -> dict:
    request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    if data is None:
        payload = None
    elif request_headers.get("Content-Type") == "application/json":
        payload = json.dumps(data).encode()
    else:
        payload = urllib.parse.urlencode(data).encode()
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request = urllib.request.Request(url, data=payload, method=method, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            body = response.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1600]
        raise RuntimeError(f"API request failed ({exc.code}): {detail}") from exc


def replace_action_secret(name: str, value: str) -> None:
    token = os.environ.get("GH_SECRETS_TOKEN", "")
    if not token:
        raise RuntimeError("GH_SECRETS_TOKEN is required for automatic token renewal.")
    owner, repo = os.environ["GITHUB_REPOSITORY"].split("/", 1)
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    base = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets"
    key_data = request_json(f"{base}/public-key", headers=headers)
    public_key = PublicKey(base64.b64decode(key_data["key"]))
    sealed = base64.b64encode(SealedBox(public_key).encrypt(value.encode())).decode()
    request_json(f"{base}/{name}", {"encrypted_value": sealed, "key_id": key_data["key_id"]}, method="PUT", headers=headers)


def refresh_instagram_token(token: str) -> str:
    query = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": token})
    result = request_json(f"https://graph.instagram.com/refresh_access_token?{query}")
    fresh = result.get("access_token")
    if not fresh:
        raise RuntimeError("Meta did not return a refreshed Instagram access token.")
    if fresh != token:
        replace_action_secret("IG_ACCESS_TOKEN", fresh)
    return fresh


def record_published(package: dict, today: str, media_id: str) -> None:
    stories = package.get("stories") or [package["story"]]
    story_urls = [story["url"] for story in stories]
    (DOCS / "published.json").write_text(json.dumps({
        "date": today,
        "media_id": media_id,
        "story_urls": story_urls,
        "story_url": story_urls[0] if story_urls else "",
    }, indent=2) + "\n", encoding="utf-8")
    seen = read_json(DOCS / "seen.json", [])
    seen_urls = set(story_urls)
    seen = [item for item in seen if item.get("url") not in seen_urls]
    seen.extend({"url": url, "published": today} for url in story_urls)
    (DOCS / "seen.json").write_text(json.dumps(seen[-120:], indent=2) + "\n", encoding="utf-8")
    write_index()


def wait_for_container(creation_id: str, token: str) -> None:
    status_url = f"https://graph.instagram.com/{creation_id}?fields=status_code,status&access_token={urllib.parse.quote(token)}"
    for _ in range(24):
        status = request_json(status_url)
        if status.get("status_code") == "FINISHED":
            return
        if status.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram image processing failed: {status.get('status', 'unknown error')}")
        time.sleep(5)
    raise RuntimeError(f"Instagram did not finish processing container {creation_id} in time.")


def publish() -> None:
    today = datetime.now(IST).date().isoformat()
    package = read_json(DOCS / "current.json", {})
    if package.get("date") != today or package.get("status") != "ready":
        raise RuntimeError("No prepared image package is available for today. Run prepare before publish.")
        return
    published = read_json(DOCS / "published.json", {})
    if published.get("date") == today:
        print("Today's post is already recorded as published; preventing a duplicate.")
        return

    token = refresh_instagram_token(os.environ["IG_ACCESS_TOKEN"])
    ig_user_id = os.environ["IG_USER_ID"]
    version = os.environ.get("META_GRAPH_VERSION", "v25.0")
    base = f"https://graph.instagram.com/{version}/{ig_user_id}"
    recent_url = f"{base}/media?" + urllib.parse.urlencode({"fields": "id,caption,timestamp", "limit": "25", "access_token": token})
    recent = request_json(recent_url).get("data", [])
    stories = package.get("stories") or [package["story"]]
    story_urls = [story["url"] for story in stories]
    for media in recent:
        caption = media.get("caption", "")
        if not any(url in caption for url in story_urls):
            continue
        posted_at = datetime.fromisoformat(media["timestamp"].replace("Z", "+00:00")).astimezone(IST).date().isoformat()
        if posted_at == today:
            record_published(package, today, media["id"])
            print("This story set is already present in today's Instagram posts; preventing a duplicate.")
            return

    image_urls = package.get("image_urls") or [package["image_url"]]
    alt_texts = package.get("alt_texts") or [package.get("alt_text", "AI Brief image")]
    if len(image_urls) == 1:
        container = request_json(f"{base}/media", {
            "image_url": image_urls[0],
            "caption": package["caption"],
            "alt_text": alt_texts[0],
            "access_token": token,
        }, method="POST")
        creation_id = container.get("id")
        if not creation_id:
            raise RuntimeError("Instagram did not return an image container ID.")
    else:
        child_ids = []
        for index, image_url in enumerate(image_urls):
            child = request_json(f"{base}/media", {
                "image_url": image_url,
                "is_carousel_item": "true",
                "alt_text": alt_texts[index] if index < len(alt_texts) else "AI Brief news carousel slide",
                "access_token": token,
            }, method="POST")
            child_id = child.get("id")
            if not child_id:
                raise RuntimeError(f"Instagram did not return a container ID for carousel image {index + 1}.")
            wait_for_container(child_id, token)
            child_ids.append(child_id)

        if len(child_ids) < 2:
            raise RuntimeError("Instagram carousels require at least two image items.")
        container = request_json(f"{base}/media", {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": package["caption"],
            "access_token": token,
        }, method="POST")
        creation_id = container.get("id")
        if not creation_id:
            raise RuntimeError("Instagram did not return a carousel container ID.")
    wait_for_container(creation_id, token)

    result = request_json(f"{base}/media_publish", {"creation_id": creation_id, "access_token": token}, method="POST")
    media_id = result.get("id")
    if not media_id:
        raise RuntimeError("Meta did not return a published carousel media ID.")
    record_published(package, today, media_id)
    print(f"Published Instagram post media ID {media_id} with {len(image_urls)} image(s).")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "publish"}:
        raise SystemExit("Usage: python pipeline.py prepare|publish")
    prepare() if sys.argv[1] == "prepare" else publish()
