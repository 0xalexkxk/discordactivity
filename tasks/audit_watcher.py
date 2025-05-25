import discord
import asyncio
import traceback
from datetime import datetime, timezone

class AuditLogWatcher:
    def __init__(self, bot):
        self.bot = bot
    
    async def run(self) -> None:
        """Continuously monitor audit logs for new ticket channels"""
        await self.bot.wait_until_ready()
        
        if not self.bot.guilds:
            print("Error: Bot is not connected to any guilds.")
            return
            
        guild_id = self.bot.config.get("guild_id")
        guild = None
        
        # Check if bot has access to the specified guild
        if guild_id:
            guild = self.bot.get_guild(guild_id)
        
        # If guild with specified ID not found, take first available
        if not guild and self.bot.guilds:
            guild = self.bot.guilds[0]
            self.bot.config["guild_id"] = guild.id
            self.bot.config_manager.save_config()
            print(f"Updated guild_id in config to {guild.id}")
            guild_id = guild.id
        
        if not guild:
            print("Error: Could not find any accessible guild.")
            return
            
        print(f"Starting audit log watcher for guild: {guild.name} (ID: {guild.id})")
        
        # Check if bot has required permissions
        bot_member = guild.get_member(self.bot.user.id)
        if not bot_member:
            print("Error: Bot is not a member of the guild.")
            return
            
        permissions = bot_member.guild_permissions
        if not permissions.view_audit_log:
            print("Warning: Bot does not have 'View Audit Log' permission.")
        
        # Get list of Sahara AI bot IDs
        sahara_bot_ids = self.bot.config.get("sahara_bot_ids", [])
        sahara_bots = {}
        
        # Find bot objects
        for bot_id in sahara_bot_ids:
            bot = guild.get_member(bot_id)
            if bot:
                sahara_bots[bot_id] = bot
                print(f"Found Sahara Bot: {bot.name} (ID: {bot.id})")
            else:
                print(f"Warning: Sahara Bot with ID {bot_id} not found in guild {guild.name}")
        
        if not sahara_bots:
            print("Warning: No Sahara Bots found in guild. Will track channels created by any bot.")
        
        # Get the initial latest audit log entry ID
        latest_entry_id = None
        try:
            async for entry in guild.audit_logs(limit=1):
                latest_entry_id = entry.id
                break
        except discord.Forbidden:
            print("Error: Bot does not have permission to view audit logs.")
            return
        
        while True:
            try:
                # Look for new channel creation events
                new_latest_id = None
                
                async for entry in guild.audit_logs(action=discord.AuditLogAction.channel_create, limit=10):
                    # Update latest entry ID for future comparisons
                    if not new_latest_id:
                        new_latest_id = entry.id
                    
                    # Skip if we've already processed this entry
                    if latest_entry_id and entry.id <= latest_entry_id:
                        break
                    
                    # Check if the channel was created by a Sahara AI bot or any other bot if none found
                    created_by_target = False
                    
                    if entry.user and entry.user.id in sahara_bot_ids:
                        created_by_target = True
                        print(f"Channel created by Sahara AI: {entry.user.name} (ID: {entry.user.id})")
                    elif not sahara_bots and entry.user and entry.user.bot:
                        # If no Sahara bots found, track channels created by any bot
                        created_by_target = True
                        print(f"Channel created by bot: {entry.user.name} (ID: {entry.user.id})")
                        
                    if created_by_target and isinstance(entry.target, discord.TextChannel):
                        # Check if it's a ticket channel by name pattern
                        channel_name = entry.target.name
                        channel_id = entry.target.id
                        if "-" in channel_name:  # Simple check for ticket format
                            # Check channel existence before adding
                            channel = guild.get_channel(channel_id)
                            if channel:
                                # Save channel ID, name and guild ID
                                self.bot.data_manager.ticket_channels[channel_id] = (channel_name, guild.id)
                                print(f"New ticket channel tracked: {channel_name} (ID: {channel_id})")
                                
                                # Generate channel link
                                channel_url = f"https://discord.com/channels/{guild.id}/{channel_id}"
                                print(f"Channel URL: {channel_url}")
                                
                                self.bot.data_manager.save_data()
                
                # Update the latest entry ID we've seen
                if new_latest_id:
                    latest_entry_id = new_latest_id
                
                # Wait before checking again
                await asyncio.sleep(10)
                
            except discord.Forbidden:
                print("Error: Lost permission to view audit logs.")
                await asyncio.sleep(60)  # Wait longer before trying again
            except Exception as e:
                print(f"Error in audit log watcher: {e}")
                traceback.print_exc()
                await asyncio.sleep(30)  # Wait longer if there was an error