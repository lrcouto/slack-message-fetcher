# slack-message-fetcher
Experiment with a tiny bot that fetches Slack messages and dumps them into .json files

Create a bot with the following token scopes:
- channels:read (list public channels)
- groups:read (list private channels)
- channels:history (read public channel messages)
- groups:history (read private channel messages)

Install the app to your workspace and save the Bot User Oauth Token.

Invite it to the channels where you want to fetch messages.

Add your Bot User OAuth Token to the .env file.

Run `slack_dump.py`
