import discord

# Files
CONFIG_FILE = "config.json"
DATA_FILE = "activity_data.json"
MESSAGES_FILE = "ticket_messages.json"

# Configure intents
INTENTS = discord.Intents.default()
INTENTS.messages = True
INTENTS.guilds = True
INTENTS.message_content = True
INTENTS.members = True
INTENTS.guild_messages = True

# Default configuration
DEFAULT_CONFIG = {
    "tracked_users": [1267999362601189400],  # Your ID
    "sahara_bot_ids": [1275351977286570056, 1335639507411664896],  # Sahara AI bot IDs
    "guild_id": 1209630079936630824,  # Your server ID
    "reports_channel_id": None  # ID for automatic reports channel
}