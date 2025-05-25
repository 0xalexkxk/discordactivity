import discord
from discord.ext import commands
import asyncio
import traceback
from datetime import datetime, timezone

# Import project modules
from config_manager import ConfigManager
from data_manager import DataManager
from tasks.scheduler import setup_scheduled_tasks
from tasks.audit_watcher import AuditLogWatcher
from utils.helpers import get_current_datetime_utc
from constants import INTENTS

class TicketBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS)
        
        # Initialize managers
        self.config_manager = ConfigManager(self)
        self.data_manager = DataManager(self)
        
        # Load configuration and data
        self.config = self.config_manager.load_config()
        self.data_manager.load_data()
        self.data_manager.load_messages()
        
        # Set debug mode
        self.debug_mode = True
        
        # Remove default help command
        self.remove_command('help')
        
        # Register command modules
        self.load_command_modules()
        
        # Setup error handlers
        self.setup_error_handlers()
        
    def load_command_modules(self):
        """Load all command modules"""
        # Import here to avoid circular imports
        from commands.admin_commands import register_admin_commands
        from commands.report_commands import register_report_commands
        from commands.utility_commands import register_utility_commands
        
        register_admin_commands(self)
        register_report_commands(self)
        register_utility_commands(self)
    
    def setup_error_handlers(self):
        """Set up error handlers for commands"""
        @self.event
        async def on_command_error(ctx, error):
            if isinstance(error, commands.MissingRequiredArgument):
                if ctx.command.name == "report":
                    await ctx.send("❌ Error: Missing required argument.\nUsage: `!report [daily,weekly,monthly]`")
                elif ctx.command.name == "manage_user":
                    await ctx.send("❌ Error: Missing required argument.\nUsage: `!manage_user [add/remove] @user`")
                elif ctx.command.name == "add_user" or ctx.command.name == "remove_user_id":
                    await ctx.send(f"❌ Error: Missing required user ID.\nUsage: `!{ctx.command.name} [user_id]`")
                elif ctx.command.name == "add_sahara_id" or ctx.command.name == "remove_sahara_id":
                    await ctx.send(f"❌ Error: Missing required bot ID.\nUsage: `!{ctx.command.name} [bot_id]`")
                else:
                    await ctx.send(f"❌ Error: Missing required argument for command `{ctx.command.name}`.\nUse `!help` for command syntax.")
            elif isinstance(error, commands.MemberNotFound):
                await ctx.send("❌ Error: User not found. Please specify a valid user.")
            elif isinstance(error, commands.MissingPermissions):
                await ctx.send("❌ Error: You need administrator permissions to use this command.")
            elif isinstance(error, commands.CommandNotFound):
                # Ignore unknown commands
                pass
            else:
                print(f"Unhandled error: {type(error).__name__}: {error}")
                traceback.print_exc()  # Print full traceback for debugging
                await ctx.send(f"❌ An error occurred: {type(error).__name__}. Please check server logs.")
    
    async def setup_hook(self) -> None:
        """Set up the bot with tasks and slash commands"""
        # Start background tasks
        setup_scheduled_tasks(self)
        
    async def on_ready(self) -> None:
        """Called when the bot is ready"""
        print(f"Logged in as {self.user.name} (ID: {self.user.id})")
        print(f"Connected to {len(self.guilds)} guild(s)")
        print(f"Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): {get_current_datetime_utc()}")
        print(f"Current User's Login: TomekCM")
        
        # Output list of connected guilds
        if self.guilds:
            print("Connected to the following guilds:")
            for guild in self.guilds:
                print(f"- {guild.name} (ID: {guild.id})")
        
        # Update guild ID in config if needed
        guild_id = self.config.get("guild_id")
        if not self.get_guild(guild_id) and self.guilds:
            self.config["guild_id"] = self.guilds[0].id
            self.config_manager.save_config()
            print(f"Updated guild_id in config to {self.guilds[0].id}")
            guild_id = self.guilds[0].id
        
        # Log tracked users and bots
        print("Currently tracking users:", self.config.get("tracked_users", []))
        print(f"Sahara Bot IDs: {self.config.get('sahara_bot_ids', [])}")
        print(f"Reports channel ID: {self.config.get('reports_channel_id')}")
        
        # Check for all known Sahara bot IDs
        await self.config_manager.check_sahara_bots()
        
        # Sync slash commands with Discord
        if guild_id:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Synchronized slash commands with guild ID {guild_id}")
        else:
            await self.tree.sync()
            print("Synchronized slash commands globally")
        
        # Check for deleted channels on startup
        deleted_count = await self.data_manager.check_and_remove_deleted_channels()
        if deleted_count > 0:
            print(f"Removed {deleted_count} deleted channel(s) during startup.")
        
        # Start audit log monitoring
        self.audit_watcher = AuditLogWatcher(self)
        self.bg_task = self.loop.create_task(self.audit_watcher.run())
        
        # Set status
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="ticket activity | !help"
        ))
    
    async def on_message(self, message: discord.Message) -> None:
        """Process messages for activity tracking"""
        try:
            # List of tracked Sahara bot IDs
            sahara_bot_ids = self.config.get("sahara_bot_ids", [])
            
            # Debug info for any message from any Sahara Bot
            if message.author.bot and message.author.id in sahara_bot_ids:
                if self.debug_mode:
                    print(f"📩 Message from Sahara Bot {message.author.name} (ID: {message.author.id}): '{message.content}'")
                
                # Check for ticket activities
                if message.channel.id in self.data_manager.ticket_channels:
                    await self.data_manager.process_sahara_message(message)
            
            # Handle messages from regular users
            elif not message.author.bot and message.channel.id in self.data_manager.ticket_channels:
                # Check if this is a tracked user
                if message.author.id in self.config.get("tracked_users", []):
                    # Record ticket being addressed
                    self.data_manager.record_activity(
                        message.author.id,
                        message.channel.id, 
                        message.channel.name,
                        "addressed"
                    )
                    
                    # Record the moderator's message for future analysis
                    self.data_manager.record_message(
                        message.author.id, 
                        message.author.name,
                        message.channel.id,
                        message.content
                    )
        except Exception as e:
            print(f"Error processing message: {e}")
            traceback.print_exc()
        
        # Process commands regardless of errors above
        try:
            await self.process_commands(message)
        except Exception as e:
            print(f"Error processing commands: {e}")
            traceback.print_exc()