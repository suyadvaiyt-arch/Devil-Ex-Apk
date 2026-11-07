# Devil Ex Apk Download Bot

Python + Aiogram 3 Telegram bot. White + Liquid Glass is the requested product direction; Telegram chat UI itself is controlled by Telegram, while this bot uses clean, compact messages and inline buttons.

## Features
- Deep links: `https://t.me/BOT_USERNAME?start=app_APPID`
- Delivers the matching APK using Telegram `file_id`
- Optional app logo, app name, version, developer, download counter
- Force-join check
- Admin-only add/list/stats/delete controls
- SQLite database

## Setup
1. Create a bot with `@BotFather` and copy its token.
2. Get your numeric Telegram user ID (for example using a trusted ID bot).
3. Make the bot an administrator in your channel so it can check membership. Give it only the permissions it needs; posting permission is not required for this download workflow.
4. Create a GitHub repository and upload these project files.
5. In Railway, deploy the GitHub repository.
6. Add Railway Variables:
   - `BOT_TOKEN`: your new BotFather token
   - `OWNER_IDS`: your numeric Telegram user ID (comma-separated for multiple admins)
   - `CHANNEL_ID`: `@yourchannel` or the channel numeric ID
   - `CHANNEL_LINK`: `https://t.me/yourchannel`
   - `WELCOME_TEXT`: `Welcome to Devil Ex Apk Download Bot!`
   - `WELCOME_BANNER_FILE_ID`: optional Telegram photo file_id
7. Deploy/redeploy. Check Railway logs for startup errors.
8. Open the bot and send `/start`, then `/admin`.

## Add an app
1. Send `/admin`.
2. Choose **Add App**.
3. Enter app name, version, developer.
4. Send the APK as a Telegram document (not as a photo/video).
5. Send the app logo as a photo, or send `/skip`.
6. The bot returns a unique deep link. Put that link behind the Download button in your channel post.

Example:
`https://t.me/YourBotUsername?start=app_a1b2c3d4`

## Important
- Railway's local filesystem may be ephemeral depending on deployment/storage configuration. Attach a persistent Railway Volume and set `DB_PATH` to a path on that volume (for example `/data/bot_data.sqlite3`) if you need the SQLite app catalogue to survive redeploys.
- Telegram bots have file-size and delivery limits that may change. Test with your APK sizes.
- Never commit `.env`, bot tokens, or other secrets to GitHub. If a token was exposed, revoke it with BotFather and use a newly generated token.
- Force-join verification requires the bot to be an administrator in the channel. Verify `CHANNEL_ID` and `CHANNEL_LINK` are correct.
