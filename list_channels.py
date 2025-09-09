import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

def list_channels():
    channels = []
    cursor = None
    while True:
        resp = client.conversations_list(
            types="public_channel,private_channel",
            limit=200,
            cursor=cursor
        )
        channels.extend(resp["channels"])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    for ch in channels:
        print(f"{ch['id']}  #{ch.get('name') or ch.get('name_normalized')}  (is_private={ch['is_private']})")

if __name__ == "__main__":
    try:
        list_channels()
    except SlackApiError as e:
        print("Slack error:", e.response.get("error", str(e)))
