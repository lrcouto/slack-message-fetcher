import os
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv


load_dotenv()
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
client = WebClient(token=SLACK_BOT_TOKEN)


DUMP_DIR = "messages"
os.makedirs(DUMP_DIR, exist_ok=True)


def fetch_channels():
    """Fetch list of channels (public + private if accessible)."""
    try:
        result = client.conversations_list(types="public_channel,private_channel")
        return result["channels"]
    except SlackApiError as e:
        print(f"Error fetching channels: {e}")
        return []


def fetch_messages(channel_id):
    """Fetch messages from a channel the bot has access to."""
    try:
        result = client.conversations_history(channel=channel_id)
        return result["messages"]
    except SlackApiError as e:
        # Ignore if bot is not in channel or lacks permission
        if e.response["error"] in ["not_in_channel", "missing_scope"]:
            print(f"Skipping channel {channel_id}: {e.response['error']}")
            return []
        else:
            raise  # re-raise unexpected errors


def save_messages(channel_name, messages):
    """Save messages to messages/<channel_name>.json"""
    filename = os.path.join(DUMP_DIR, f"{channel_name}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(messages)} messages to {filename}")


def main():
    channels = fetch_channels()
    for channel in channels:
        channel_id = channel["id"]
        channel_name = channel["name"]
        print(f"\n=== Fetching messages from #{channel_name} ===")
        messages = fetch_messages(channel_id)
        print(f"Retrieved {len(messages)} messages")
        if messages:
            save_messages(channel_name, messages)


if __name__ == "__main__":
    main()
