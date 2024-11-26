# Installation and Configuration Guide for NekoShell
This guide will walk you through the process of setting up and configuring NekoShell for your Discord server.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (optional, for cloning the repository)

## Step 1: Clone the Repository

If you haven't already, clone the NekoShell repository:

```bash
git clone https://github.com/h3nr1d3v/NekoShell.git
cd NekoShell
```

## Step 2: Set Up a Virtual Environment (Recommended)

It's recommended to use a virtual environment to avoid conflicts with other Python projects:

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

## Step 3: Install Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

## Step 4: Set Up API Keys and Tokens

1. **Discord Bot Token**:

- Go to the [Discord Developer Portal](https://discord.com/developers/applications)
- Create a new application and add a bot to it.
- Give the bot "Administrator" permissions.
- Copy the bot token.

2. **OpenAI API Key**:

- Go to the [OpenAI website](https://openai.com/)
- Navigate to the API section and create a new API key.

3. **Stability API Key**:
- Visit the [Stability AI website](https://stability.ai/)
- Generate an API key for image generation.

4. **Spotify API Credentials**:
- Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
- Create a new app to get your Client ID and Client Secret.

5. **Generate WebServer API Key**:
- Run the following command in your terminal:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 5: Configure Environment Variables

Create a `.env` file in the root directory of the project and add the following:

```bash
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=your_openai_api_key
STABILITY_API_KEY=your_stability_api_key
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
WEBSERVER_API_KEY=your_generated_webserver_api_key
```
Replace the placeholders with your actual API keys and tokens.

## Step 6: Configure Discord Server Settings

1. Enable Developer Mode in your Discord client (User Settings > Advanced > Developer Mode).
2. Create the necessary channels in your Discord server for welcome messages, logs, etc.
3. Right-click on each channel and copy the channel ID.

## Step 7: Update Channel IDs in the Code

1. Open `cogs/moderation.py` and update the following constants with your channel IDs:

```bash
WELCOME_CHANNEL_ID = #ID channels here
LEFT_CHANNEL_ID = #ID channels here 
BANNED_CHANNEL_ID = #ID channels here
UNBANNED_CHANNEL_ID = #ID channels here
WARNINGS_CHANNEL_ID = #ID channels here
```
2. Open `cogs/welcome.py` and update the same constants.
3. Open `cogs/logs.py` and update the following:

```bash
self.log_channel_id = # Replace with your log channel ID
self.ignored_channels = set()  # Add channel IDs here to ignore
```

## Step 8: Set Up YouTube Cookies

1. Create a file named `youtube_cookies.txt` in the root directory of the project.
2. Add the following header to the file:
```bash
# Netscape HTTP Cookie File
# https://www.youtube.com
# This is a generated file!  Do not edit.
```
3. Add the following cookies to the file (replace values with your actual YouTube cookies):

- SID
- HSID
- SSID
- APISID
- SAPISID
- __Secure-1PSID
- __Secure-3PSID
- __Secure-1PAPISID
- __Secure-3PAPISID
- LOGIN_INFO
- PREF
- SIDCC
- CONSISTENCY

Example format for each cookie:

```bash
.youtube.com	TRUE	/	TRUE	18473621872	HSID	NSN12IUnds9h23fs2
```
To find these cookies manually:

1. Open YouTube in your browser.
2. Open Developer Tools (Ctrl + Shift + I or Cmd + Option + I).
3. Go to the Application tab (Chrome/Edge) or Storage tab (Firefox).
4. Under Cookies, select [https://www.youtube.com](https://www.youtube.com)
5. Copy the required cookies.

## Step 9: Run the Bot

With everything set up, you can now run the bot:

```bash
python main.py
```
