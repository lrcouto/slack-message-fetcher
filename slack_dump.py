import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from tqdm import tqdm

load_dotenv()
TOKEN = os.environ["SLACK_BOT_TOKEN"]
client = WebClient(token=TOKEN)

EXPORT_DIR = Path("slack_export")
EXPORT_DIR.mkdir(exist_ok=True)

def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def rate_limit_sleep(e: SlackApiError):
    # If ratelimited, Slack sends HTTP 429 + Retry-After header
    try:
        retry_after = int(getattr(e.response, "headers", {}).get("Retry-After", "1"))
    except Exception:
        retry_after = 1
    time.sleep(retry_after + 1)

@retry(
    retry=retry_if_exception_type(SlackApiError),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    stop=stop_after_attempt(5)
)
def call_with_retry(func, **kwargs):
    try:
        return func(**kwargs)
    except SlackApiError as e:
        if e.response is not None and getattr(e.response, "status_code", None) == 429:
            rate_limit_sleep(e)
        raise

def list_all_channels():
    channels = []
    cursor = None
    while True:
        resp = call_with_retry(
            client.conversations_list,
            types="public_channel,private_channel",
            limit=200,
            cursor=cursor
        )
        channels.extend(resp["channels"])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(0.5)  # gentle pacing
    return channels

def fetch_channel_history(channel_id):
    """Fetch all top-level messages for a channel (no replies yet)."""
    messages = []
    cursor = None
    while True:
        resp = call_with_retry(
            client.conversations_history,
            channel=channel_id,
            limit=200,
            cursor=cursor
        )
        messages.extend(resp["messages"])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(0.5)
    return messages

def fetch_thread_replies(channel_id, thread_ts):
    """Fetch a full thread given its root ts."""
    replies = []
    cursor = None
    while True:
        resp = call_with_retry(
            client.conversations_replies,
            channel=channel_id,
            ts=thread_ts,
            limit=200,
            cursor=cursor
        )
        # API returns the root message as the first element; keep full set.
        replies.extend(resp["messages"])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(0.5)
    return replies

def enrich_with_threads(channel_id, messages):
    """Attach full thread messages to each thread root as msg['replies']."""
    for msg in messages:
        if "thread_ts" in msg and msg.get("ts") == msg.get("thread_ts"):
            replies = fetch_thread_replies(channel_id, msg["thread_ts"])
            msg["replies"] = replies
            time.sleep(0.3)
    return messages

def dump_channel(channel, run_stamp):
    channel_id = channel["id"]
    channel_name = channel.get("name") or channel.get("name_normalized") or channel_id
    print(f"\nDumping #{channel_name} ({channel_id}) ...")

    messages = fetch_channel_history(channel_id)
    messages = enrich_with_threads(channel_id, messages)

    out = {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "is_private": channel.get("is_private", False),
        "fetched_at": iso_now(),
        "message_count": len(messages),
        "messages": messages,
    }

    # Write a timestamped snapshot per run
    chan_dir = EXPORT_DIR / channel_name
    chan_dir.mkdir(parents=True, exist_ok=True)
    out_path = chan_dir / f"{run_stamp}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(messages)} messages -> {out_path}")

def main():
    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    channels = list_all_channels()
    print(f"Found {len(channels)} channels.")
    for ch in tqdm(channels, desc="Channels"):
        try:
            dump_channel(ch, run_stamp)
        except SlackApiError as e:
            err = e.response.get("error") if e.response else str(e)
            print(f"Error dumping channel {ch.get('name')}: {err}")

if __name__ == "__main__":
    main()
