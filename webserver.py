from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from threading import Thread
import os
import psutil
import datetime
import logging
from functools import wraps

app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Secret key for authentication (use an environment variable in production)
API_KEY = os.getenv('WEBSERVER_API_KEY', 'your-secret-key-here')


def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-API-Key') and request.headers.get('X-API-Key') == API_KEY:
            return view_function(*args, **kwargs)
        else:
            return jsonify({"error": "Invalid or missing API Key"}), 403
    return decorated_function


@app.route('/')
def home():
    return render_template_string("""
    <html>
        <head>
            <title>NekoShell Discord Bot Webserver</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; background-color: #f0f0f0; }
                h1 { color: #333; }
                p { margin-bottom: 10px; }
                .container { max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome to the NekoShell Discord Bot Webserver</h1>
                <p>This server provides various endpoints to interact with and monitor the NekoShell Discord bot.</p>
                <p>Available endpoints:</p>
                <ul>
                    <li>/status - Check the bot's status</li>
                    <li>/stats - Get bot statistics</li>
                    <li>/guilds - List all guilds the bot is in</li>
                    <li>/commands - List all available bot commands</li>
                    <li>/cogs - List all loaded cogs</li>
                </ul>
                <p>Note: Some endpoints require authentication with an API key.</p>
            </div>
        </body>
    </html>
    """)


@app.route('/status')
@require_api_key
def status():
    return jsonify({
        "status": "Bot is running!",
        "uptime": str(datetime.timedelta(seconds=int(psutil.Process().create_time() - app.config['bot'].start_time))),
        "latency": f"{app.config['bot'].latency * 1000:.2f} ms"
    })


@app.route('/stats')
@require_api_key
def stats():
    process = psutil.Process()
    return jsonify({
        "guilds": len(app.config['bot'].guilds),
        "users": len(set(app.config['bot'].get_all_members())),
        "commands": len(app.config['bot'].commands),
        "cogs": len(app.config['bot'].cogs),
        "memory_usage": f"{process.memory_info().rss / 1024 / 1024:.2f} MB",
        "cpu_usage": f"{psutil.cpu_percent()}%"
    })


@app.route('/guilds')
@require_api_key
def guilds():
    return jsonify([
        {"id": guild.id, "name": guild.name, "member_count": guild.member_count}
        for guild in app.config['bot'].guilds
    ])


@app.route('/commands')
def commands():
    return jsonify([
        {
            "name": command.name,
            "description": command.help,
            "cog": command.cog_name if command.cog else None
        }
        for command in app.config['bot'].commands
    ])


@app.route('/cogs')
@require_api_key
def cogs():
    return jsonify([
        {
            "name": name,
            "commands": [cmd.name for cmd in cog.get_commands()]
        }
        for name, cog in app.config['bot'].cogs.items()
    ])


@app.route('/logs')
@require_api_key
def logs():
    try:
        with open('discord.log', 'r') as log_file:
            return log_file.read()
    except FileNotFoundError:
        return "Log file not found", 404


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return jsonify({"error": "Internal Server Error"}), 500


def run_flask():
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)


def start_webserver(bot):
    app.config['bot'] = bot
    webserver_thread = Thread(target=run_flask)
    webserver_thread.daemon = True
    webserver_thread.start()
    logger.info(f"Webserver started on port {
                int(os.environ.get('PORT', 8000))}")


if __name__ == "__main__":
    print("This script should be imported and run from main.py")
