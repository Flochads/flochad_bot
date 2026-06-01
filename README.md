# Discord Activity Tracker Bot

This bot tracks usage activity for a specific target bot (e.g., Mudae) and generates beautiful heatmaps showing when the server or individual users are most active.

# BRO IF you do a change then edit this here bro: basic.py LAST_UPDATED

## Features
- Tracks prefix commands (`.`) in a specified tracking channel.
- Tracks slash commands executed by users on the target bot.
- Stores data asynchronously in an SQLite database.
- Generates activity heatmaps by hour of the day and day of the week.

## Setup

1. **Install Dependencies**
   Make sure you have Python 3.10+ installed. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Rename `.env.example` to `.env` and fill in the details:
   - `DISCORD_TOKEN`: Your bot's token from the Discord Developer Portal.
   - `TARGET_BOT_ID`: The User ID of the bot to track (e.g., Mudae is `432610292342587392`).
   - `TARGET_PREFIX`: The prefix to track for the target bot.
   - `TRACKING_CHANNEL_ID`: The ID of the channel where prefix tracking should occur.

3. **Run the Bot**
   ```bash
   python bot.py
   ```

## Commands

- `/ping`: Health check to see bot latency.
- `/echo <message>`: Repeats the given message.
- `/stats server`: Generates a heatmap of overall server activity.
- `/stats user <user>`: Generates a heatmap of a specific user's activity.
- `/stats command <command_name>`: Generates a heatmap for a specific command.

## Important Note
For the bot to read prefix commands correctly, ensure that the **Message Content Intent** is enabled in your Discord Developer Portal for this bot application.
