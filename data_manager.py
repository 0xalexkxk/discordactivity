import os
import json
import re
from datetime import datetime, timezone
from typing import Dict, Set, List, Optional, Tuple, Union, Any
from constants import DATA_FILE, MESSAGES_FILE

class DataManager:
    def __init__(self, bot):
        self.bot = bot
        
        # Data structures
        self.ticket_channels: Dict[int, Tuple[str, int]] = {}  # channel_id -> (channel_name, guild_id)
        
        # Activity data structure
        self.user_activity = {
            "daily": {},    # user_id -> {"addressed": [channel_ids], "closed": [channel_ids], "deleted": [channel_ids]}
            "weekly": {},   # user_id -> {"addressed": [channel_ids], "closed": [channel_ids], "deleted": [channel_ids]}
            "monthly": {},  # user_id -> {"addressed": [channel_ids], "closed": [channel_ids], "deleted": [channel_ids]}
        }
        
        # Ticket messages structure
        self.ticket_messages = {}  # channel_id -> [{"user_id": id, "username": name, "timestamp": time, "content": msg}]
    
    def load_data(self) -> None:
        """Load activity data from file"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    data = json.load(f)
                    
                    # Convert channel IDs and user IDs to integers
                    if "ticket_channels" in data:
                        if isinstance(data["ticket_channels"], list):
                            # Old format - update it
                            self.ticket_channels = {int(channel_id): ("unknown", self.bot.config.get("guild_id", 0)) 
                                               for channel_id in data["ticket_channels"]}
                        else:
                            # New format with names and guild IDs
                            self.ticket_channels = {int(channel_id): (info[0], int(info[1])) 
                                               for channel_id, info in data["ticket_channels"].items()}
                    
                    # Load activity data
                    if "user_activity" in data:
                        for period in ["daily", "weekly", "monthly"]:
                            if period in data["user_activity"]:
                                for user_id_str, actions in data["user_activity"][period].items():
                                    user_id = int(user_id_str)
                                    self.user_activity[period][user_id] = {}
                                    for action_type, channel_list in actions.items():
                                        self.user_activity[period][user_id][action_type] = [int(ch_id) for ch_id in channel_list]
            except Exception as e:
                print(f"Error loading data: {e}")
                self.initialize_data()  # Create a new data structure
        else:
            self.initialize_data()  # Create a new data structure
    
    def load_messages(self) -> None:
        """Load ticket messages from file"""
        if os.path.exists(MESSAGES_FILE):
            try:
                with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert channel IDs to integers
                    self.ticket_messages = {int(channel_id): messages for channel_id, messages in data.items()}
            except Exception as e:
                print(f"Error loading ticket messages: {e}")
                self.ticket_messages = {}
        else:
            self.ticket_messages = {}
            self.save_messages()
    
    def save_messages(self) -> None:
        """Save ticket messages to file"""
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            # Convert channel IDs to strings for JSON serialization
            data = {str(channel_id): messages for channel_id, messages in self.ticket_messages.items()}
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def initialize_data(self) -> None:
        """Initialize empty data structures"""
        self.user_activity = {
            "daily": {},
            "weekly": {},
            "monthly": {},
        }
        
        self.save_data()

    def save_data(self) -> None:
        """Save activity data to file"""
        data = {
            "ticket_channels": {str(channel_id): [name, str(guild_id)] 
                              for channel_id, (name, guild_id) in self.ticket_channels.items()},
            
            "user_activity": {
                period: {
                    str(user_id): {
                        action_type: [str(ch_id) for ch_id in channel_ids]
                        for action_type, channel_ids in actions.items()
                    }
                    for user_id, actions in period_data.items()
                }
                for period, period_data in self.user_activity.items()
            }
        }
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def record_activity(self, user_id: int, channel_id: int, channel_name: str, action_type: str) -> None:
        """Record user activity with the specified action type"""
        if user_id not in self.bot.config.get("tracked_users", []):
            if self.bot.debug_mode:
                print(f"⚠️ User {user_id} is not in tracked users list - activity not recorded")
            return
            
        now = datetime.now(timezone.utc)
        
        # Record activity for all periods
        for period in ["daily", "weekly", "monthly"]:
            # Initialize data structures if needed
            if user_id not in self.user_activity[period]:
                self.user_activity[period][user_id] = {"addressed": [], "closed": [], "deleted": []}
            
            # Add the channel to the appropriate action list if not already there
            if channel_id not in self.user_activity[period][user_id].get(action_type, []):
                if action_type not in self.user_activity[period][user_id]:
                    self.user_activity[period][user_id][action_type] = []
                    
                self.user_activity[period][user_id][action_type].append(channel_id)
                if self.bot.debug_mode or action_type in ["closed", "deleted"]:
                    print(f"[{now}] ✅ {action_type.title()} activity recorded: User {user_id} on channel {channel_name} for {period}")
        
        # Save data
        self.save_data()
    
    def record_message(self, user_id: int, username: str, channel_id: int, message_content: str) -> None:
        """Record moderator's message in a ticket"""
        if channel_id not in self.ticket_channels:
            return
            
        # Get current time in UTC
        now = datetime.now(timezone.utc)
        timestamp = now.isoformat()
        
        # Create structure for channel if it doesn't exist
        if channel_id not in self.ticket_messages:
            self.ticket_messages[channel_id] = []
            
        # Add message
        message_data = {
            "user_id": user_id,
            "username": username,
            "timestamp": timestamp,
            "content": message_content
        }
        
        self.ticket_messages[channel_id].append(message_data)
        
        # Save data
        self.save_messages()
    
    async def check_and_remove_deleted_channels(self) -> int:
        """Check for and remove deleted channels, return count of removed channels"""
        if not self.ticket_channels:
            return 0
            
        # Create copy of dictionary
        channels_to_check = dict(self.ticket_channels)
        deleted_count = 0
        
        for channel_id, (name, guild_id) in channels_to_check.items():
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
                
            channel = guild.get_channel(channel_id)
            if not channel:
                if channel_id in self.ticket_channels:
                    del self.ticket_channels[channel_id]
                    deleted_count += 1
                    
                    # Also remove channel from recorded messages
                    if channel_id in self.ticket_messages:
                        del self.ticket_messages[channel_id]
        
        if deleted_count > 0:
            self.save_data()
            self.save_messages()
            
        return deleted_count
    
    async def process_sahara_message(self, message):
        """Process message from Sahara bot for ticket activities"""
        content = message.content
        
        # For closed tickets
        if "closed the ticket" in content.lower():
            if self.bot.debug_mode:
                print(f"🔍 Found closed ticket pattern in #{message.channel.name}: '{content}'")
            
            # Check for mentions
            if message.mentions:
                for mention in message.mentions:
                    user_id = mention.id
                    if user_id in self.bot.config.get("tracked_users", []):
                        self.record_activity(
                            user_id,
                            message.channel.id, 
                            message.channel.name,
                            "closed"
                        )
                        print(f"✅ Recorded 'closed' activity for user {mention.name} in channel {message.channel.name}")
                    elif self.bot.debug_mode:
                        print(f"⚠️ User {mention.name} (ID: {mention.id}) not in tracked list - activity not recorded")
            else:
                # Alternate approach - try to find ID through regex (for old mention formats)
                user_match = re.search(r"<@!?(\d+)>", content)
                if user_match:
                    user_id = int(user_match.group(1))
                    if user_id in self.bot.config.get("tracked_users", []):
                        self.record_activity(
                            user_id,
                            message.channel.id,
                            message.channel.name,
                            "closed"
                        )
                        print(f"✅ Recorded 'closed' activity for user ID {user_id} in channel {message.channel.name}")
        
        # For deleted tickets
        elif "deleted the ticket" in content.lower():
            if self.bot.debug_mode:
                print(f"🔍 Found deleted ticket pattern in #{message.channel.name}: '{content}'")
            
            # Check for mentions
            if message.mentions:
                for mention in message.mentions:
                    user_id = mention.id
                    if user_id in self.bot.config.get("tracked_users", []):
                        self.record_activity(
                            user_id,
                            message.channel.id,
                            message.channel.name,
                            "deleted"
                        )
                        print(f"✅ Recorded 'deleted' activity for user {mention.name} in channel {message.channel.name}")
                    elif self.bot.debug_mode:
                        print(f"⚠️ User {mention.name} (ID: {mention.id}) not in tracked list - activity not recorded")
            else:
                # Alternate approach using regex
                user_match = re.search(r"<@!?(\d+)>", content)
                if user_match:
                    user_id = int(user_match.group(1))
                    if user_id in self.bot.config.get("tracked_users", []):
                        self.record_activity(
                            user_id,
                            message.channel.id,
                            message.channel.name,
                            "deleted"
                        )
                        print(f"✅ Recorded 'deleted' activity for user ID {user_id} in channel {message.channel.name}")