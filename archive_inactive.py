import os
import time
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

INACTIVE_DAYS = 30
ARCHIVE_PREFIX = "z-archive-"
PROTECTED = {
    "team-general", "team-ops", "team-strategy",
    "team-leadership", "fulfillment", "consults",
    "audit-intake", "sales-pipeline", "sales-bots"
}

def get_all_channels():
    channels = []
    cursor = None
    while True:
        resp = client.conversations_list(
            types="public_channel",
            exclude_archived=True,
            limit=200,
            cursor=cursor
        )
        channels.extend(resp["channels"])
        cursor = resp["response_metadata"].get("next_cursor")
        if not cursor:
            break
    return channels

def days_since_last_message(channel_id):
    try:
        resp = client.conversations_history(channel=channel_id, limit=1)
        msgs = resp.get("messages", [])
        if not msgs:
            return 9999
        last_ts = float(msgs[0]["ts"])
        last_date = datetime.fromtimestamp(last_ts)
        return (datetime.now() - last_date).days
    except SlackApiError:
        return None

def run():
    channels = get_all_channels()
    for ch in channels:
        name = ch["name"]
        if name in PROTECTED:
            continue
        if name.startswith(ARCHIVE_PREFIX):
            days_inactive = days_since_last_message(ch["id"])
            if days_inactive and days_inactive >= INACTIVE_DAYS:
                print(f"Archiving: #{name} ({days_inactive}d inactive)")
                client.conversations_archive(channel=ch["id"])
            continue
        if name.startswith("client-"):
            days_inactive = days_since_last_message(ch["id"])
            if days_inactive and days_inactive >= INACTIVE_DAYS:
                new_name = ARCHIVE_PREFIX + name
                print(f"Staging for archive: #{name} -> #{new_name}")
                client.conversations_rename(channel=ch["id"], name=new_name)
        time.sleep(1)

if __name__ == "__main__":
    run()
