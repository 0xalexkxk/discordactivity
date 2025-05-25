import json
import os
from discord.ext import tasks
from datetime import datetime, timezone
from constants import CONFIG_FILE, DEFAULT_CONFIG

class ConfigManager:
    def __init__(self, bot):
        self.bot = bot
    
    def load_config(self) -> dict:
        """Load bot configuration from file or create default"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    
                    # Update config if it uses old format with one bot ID
                    if "sahara_bot_id" in config and "sahara_bot_ids" not in config:
                        config["sahara_bot_ids"] = [
                            config.get("sahara_bot_id"),
                            1275351977286570056,
                            1335639507411664896
                        ]
                    
                    # Add reports channel key if it doesn't exist
                    if "reports_channel_id" not in config:
                        config["reports_channel_id"] = None
                    
                    return config
            except Exception as e:
                print(f"Error loading config: {e}")
                return DEFAULT_CONFIG
        else:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG

    def save_config(self) -> None:
        """Save configuration to file"""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.bot.config, f, indent=4)
    
    def _cleanup_invalid_users(self):
        """Clean up the list of tracked users from invalid IDs"""
        # List of valid user IDs to track
        valid_user_ids = [1267999362601189400, 221408030216945664, 991008353423593552, 1093091523459031103, 
                          762499331202351134, 847392052430110760, 970664206691086336, 328825179499397121, 
                          834916126956847174, 894030014331359283, 1150390703361380383, 1039103531891834900, 
                          791013267391905832]
        
        # Clean the list and add only valid IDs
        self.bot.config["tracked_users"] = valid_user_ids
        self.save_config()
        print(f"Cleaned up user list. Now tracking: {valid_user_ids}")
        
        # Update the list of Sahara AI bot IDs if using obsolete format
        if "sahara_bot_id" in self.bot.config and "sahara_bot_ids" not in self.bot.config:
            self.bot.config["sahara_bot_ids"] = [
                self.bot.config.get("sahara_bot_id"),
                1275351977286570056,
                1335639507411664896
            ]
            # Remove old key
            if "sahara_bot_id" in self.bot.config:
                del self.bot.config["sahara_bot_id"]
            self.save_config()
            print(f"Updated Sahara bot IDs list: {self.bot.config['sahara_bot_ids']}")
    
    async def check_sahara_bots(self) -> None:
        """Check and update Sahara Bot IDs configuration"""
        sahara_bot_ids = self.bot.config.get('sahara_bot_ids', [])
        print(f"Current Sahara Bot IDs in config: {sahara_bot_ids}")
        
        # Check for mandatory known Sahara bot IDs
        expected_ids = [1275351977286570056, 1335639507411664896]
        should_update = False
        
        for expected_id in expected_ids:
            if expected_id not in sahara_bot_ids:
                print(f"Adding missing Sahara Bot ID: {expected_id}")
                sahara_bot_ids.append(expected_id)
                should_update = True
        
        if should_update:
            self.bot.config["sahara_bot_ids"] = sahara_bot_ids
            self.save_config()
            print(f"Updated sahara_bot_ids in config to {sahara_bot_ids}")
        
        # If using obsolete format with single ID, convert it
        if "sahara_bot_id" in self.bot.config:
            old_id = self.bot.config.get("sahara_bot_id")
            if old_id and old_id not in sahara_bot_ids:
                sahara_bot_ids.append(old_id)
                self.bot.config["sahara_bot_ids"] = sahara_bot_ids
                del self.bot.config["sahara_bot_id"]
                self.save_config()
                print(f"Converted legacy sahara_bot_id {old_id} to sahara_bot_ids list")