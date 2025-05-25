import discord
from discord.ext import commands
import asyncio
import traceback

def register_admin_commands(bot):
    """Register all admin commands with the bot"""
    
    @bot.command(name="manage_user", help="Add/remove user from tracking: !manage_user [add/remove] @user")
    async def manage_user_cmd(ctx, action: str = None, user: discord.Member = None):
        if not action or not user:
            await ctx.send("❌ Error: Please specify both action and user.\nExample: `!manage_user add @username` or `!manage_user remove @username`")
            return
                
        if action.lower() not in ["add", "remove"]:
            await ctx.send("❌ Error: Invalid action. Use 'add' or 'remove'.")
            return
                
        await manage_user_command(bot, ctx, action.lower(), user)
    
    @bot.command(name="add_user", help="Add user to tracking list by ID: !add_user [user_id]")
    @commands.has_permissions(administrator=True)
    async def add_user_cmd(ctx, user_id: int):
        tracked_users = bot.config.get("tracked_users", [])
        
        if user_id in tracked_users:
            await ctx.send(f"⚠️ User with ID {user_id} is already in the tracked users list.")
            return
        
        try:
            # Try to find user by ID to verify
            user = await bot.fetch_user(user_id)
            tracked_users.append(user_id)
            bot.config["tracked_users"] = tracked_users
            bot.config_manager.save_config()
            await ctx.send(f"✅ Added {user.name} (ID: {user_id}) to tracked users.")
        except discord.NotFound:
            await ctx.send(f"❌ Error: Could not find user with ID {user_id}. Is the ID correct?")
        except Exception as e:
            await ctx.send(f"❌ Error adding user: {str(e)}")
    
    @bot.command(name="remove_user_id", help="Remove user from tracking by ID: !remove_user_id [user_id]")
    @commands.has_permissions(administrator=True)
    async def remove_user_id_cmd(ctx, user_id: int):
        tracked_users = bot.config.get("tracked_users", [])
        
        if user_id not in tracked_users:
            await ctx.send(f"⚠️ User with ID {user_id} is not in the tracked users list.")
            return
                
        tracked_users.remove(user_id)
        bot.config["tracked_users"] = tracked_users
        bot.config_manager.save_config()
        await ctx.send(f"✅ Removed user with ID {user_id} from tracked users.")
    
    @bot.command(name="add_channel", help="Add existing channel to tracking: !add_channel [link or ID]")
    @commands.has_permissions(administrator=True)
    async def add_channel_cmd(ctx, channel_reference):
        try:
            # Check if it's a link or ID
            if channel_reference.isdigit():
                # It's a channel ID
                channel_id = int(channel_reference)
                guild_id = ctx.guild.id
            else:
                # Try to parse Discord link
                # Link format: https://discord.com/channels/guild_id/channel_id
                parts = channel_reference.strip('/').split('/')
                if len(parts) >= 7 and parts[2] == "discord.com" and parts[3] == "channels":
                    guild_id = int(parts[4])
                    channel_id = int(parts[5])
                else:
                    await ctx.send("❌ Error: Invalid channel link or ID. Use either a channel ID or a Discord channel link.")
                    return
            
            # Get guild object
            guild = bot.get_guild(guild_id)
            if not guild:
                await ctx.send(f"❌ Error: Cannot access guild with ID {guild_id}.")
                return
            
            # Get channel object
            channel = guild.get_channel(channel_id)
            if not channel:
                await ctx.send(f"❌ Error: Channel with ID {channel_id} not found in guild {guild.name}.")
                return
            
            # Check if channel is already being tracked
            if channel_id in bot.data_manager.ticket_channels:
                await ctx.send(f"⚠️ Channel {channel.name} is already being tracked.")
                return
            
            # Add channel to tracking list
            bot.data_manager.ticket_channels[channel_id] = (channel.name, guild.id)
            bot.data_manager.save_data()
            
            # Confirmation
            await ctx.send(f"✅ Added channel **{channel.name}** to tracking list.")
            
        except Exception as e:
            await ctx.send(f"❌ Error adding channel: {str(e)}")
            traceback.print_exc()
    
    @bot.command(name="bulk_add_channels", help="Add multiple channels to tracking: !bulk_add_channels [link1] [link2] ...")
    @commands.has_permissions(administrator=True)
    async def bulk_add_channels_cmd(ctx, *channel_references):
        if not channel_references:
            await ctx.send("❌ Error: Please provide at least one channel link or ID.")
            return
        
        added_count = 0
        already_tracked = 0
        errors = 0
        
        status_message = await ctx.send(f"🔍 Processing {len(channel_references)} channels...")
        
        for reference in channel_references:
            try:
                # Check if it's a link or ID
                if reference.isdigit():
                    # It's a channel ID
                    channel_id = int(reference)
                    guild_id = ctx.guild.id
                else:
                    # Try to parse Discord link
                    parts = reference.strip('/').split('/')
                    if len(parts) >= 7 and parts[2] == "discord.com" and parts[3] == "channels":
                        guild_id = int(parts[4])
                        channel_id = int(parts[5])
                    else:
                        print(f"Invalid channel reference: {reference}")
                        errors += 1
                        continue
                
                # Get guild object
                guild = bot.get_guild(guild_id)
                if not guild:
                    print(f"Cannot access guild with ID {guild_id}")
                    errors += 1
                    continue
                
                # Get channel object
                channel = guild.get_channel(channel_id)
                if not channel:
                    print(f"Channel with ID {channel_id} not found in guild {guild.name}")
                    errors += 1
                    continue
                
                # Check if channel is already tracked
                if channel_id in bot.data_manager.ticket_channels:
                    print(f"Channel {channel.name} is already tracked")
                    already_tracked += 1
                    continue
                
                # Add channel to tracking list
                bot.data_manager.ticket_channels[channel_id] = (channel.name, guild.id)
                added_count += 1
                
            except Exception as e:
                print(f"Error processing channel reference {reference}: {e}")
                errors += 1
        
        # Save data only if channels were added
        if added_count > 0:
            bot.data_manager.save_data()
        
        # Update status message with results
        result = f"✅ Processed {len(channel_references)} channels:\n"
        result += f"• Added: **{added_count}**\n"
        if already_tracked > 0:
            result += f"• Already tracked: **{already_tracked}**\n"
        if errors > 0:
            result += f"• Errors: **{errors}**\n"
        
        await status_message.edit(content=result)
    
    @bot.command(name="add_sahara_id", help="Add a Sahara Bot ID to monitoring list: !add_sahara_id [bot_id]")
    @commands.has_permissions(administrator=True)
    async def add_sahara_id_cmd(ctx, bot_id: int):
        sahara_bot_ids = bot.config.get("sahara_bot_ids", [])
        
        if bot_id in sahara_bot_ids:
            await ctx.send(f"⚠️ Bot ID {bot_id} is already in the monitoring list.")
            return
                
        sahara_bot_ids.append(bot_id)
        bot.config["sahara_bot_ids"] = sahara_bot_ids
        bot.config_manager.save_config()
        await ctx.send(f"✅ Added bot ID {bot_id} to Sahara bot monitoring list.")
    
    @bot.command(name="remove_sahara_id", help="Remove a Sahara Bot ID from monitoring list: !remove_sahara_id [bot_id]")
    @commands.has_permissions(administrator=True)
    async def remove_sahara_id_cmd(ctx, bot_id: int):
        sahara_bot_ids = bot.config.get("sahara_bot_ids", [])
        
        if bot_id not in sahara_bot_ids:
            await ctx.send(f"⚠️ Bot ID {bot_id} is not in the monitoring list.")
            return
                
        sahara_bot_ids.remove(bot_id)
        bot.config["sahara_bot_ids"] = sahara_bot_ids
        bot.config_manager.save_config()
        await ctx.send(f"✅ Removed bot ID {bot_id} from Sahara bot monitoring list.")
    
    @bot.command(name="debug", help="Toggle debug mode: !debug [on/off]")
    @commands.has_permissions(administrator=True)
    async def debug_cmd(ctx, state: str):
        if state.lower() == "on":
            bot.debug_mode = True
            await ctx.send("✅ Debug mode turned ON. Detailed logging will be shown.")
        elif state.lower() == "off":
            bot.debug_mode = False
            await ctx.send("✅ Debug mode turned OFF.")
        else:
            await ctx.send("❌ Invalid option. Use 'on' or 'off'.")
    
    @bot.command(name="reset_users", help="Reset tracked users list to default")
    @commands.has_permissions(administrator=True)
    async def reset_users_cmd(ctx):
        bot.config_manager._cleanup_invalid_users()
        await ctx.send("✅ Tracked users list has been reset to default.")
    
    @bot.command(name="cleanup_tickets", help="Remove deleted channels from tracking")
    @commands.has_permissions(administrator=True)
    async def cleanup_tickets_cmd(ctx):
        await cleanup_deleted_channels(bot, ctx)
    
    @bot.command(name="reset_all_data", help="Reset all statistics and activity data (Admin only)")
    @commands.has_permissions(administrator=True)
    async def reset_all_data_cmd(ctx):
        """Reset all tracked data to start fresh"""
        confirmation_msg = await ctx.send("⚠️ **WARNING**: This will delete ALL activity data and statistics. Are you sure? Reply with `yes` to confirm.")
        
        try:
            # Wait for confirmation
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "yes"
            
            # Wait for 30 seconds for confirmation
            await bot.wait_for('message', check=check, timeout=30.0)
            
            # Reset all data structures
            bot.data_manager.user_activity = {
                "daily": {},
                "weekly": {},
                "monthly": {},
            }
            
            # Reset all messages data
            bot.data_manager.ticket_messages = {}
            
            # Save empty data
            bot.data_manager.save_data()
            bot.data_manager.save_messages()
            
            await ctx.send("✅ All activity data has been reset! Statistics are now clean.")
            
        except asyncio.TimeoutError:
            await confirmation_msg.edit(content="⚠️ Reset operation cancelled - confirmation timeout.")
    
    @bot.command(name="set_reports_channel", help="Set channel for automatic reports: !set_reports_channel [channel_id]")
    @commands.has_permissions(administrator=True)
    async def set_reports_channel_cmd(ctx, channel_id: int = None):
        if channel_id is None:
            await ctx.send("❌ Error: Please specify a channel ID.\nUsage: `!set_reports_channel [channel_id]`")
            return
        
        try:
            # Check if the channel exists and bot has permission to send messages there
            channel = bot.get_channel(channel_id)
            if not channel:
                await ctx.send(f"❌ Error: Channel with ID {channel_id} not found. Make sure the bot has access to it.")
                return
            
            # Save the channel ID to config
            bot.config["reports_channel_id"] = channel_id
            bot.config_manager.save_config()
            await ctx.send(f"✅ Set {channel.mention} as the reports channel. Automatic reports will be sent there.")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
            traceback.print_exc()
    
    @bot.command(name="update_stats", help="Update all statistics")
    @commands.has_permissions(administrator=True)
    async def update_stats_cmd(ctx):
        try:
            message = await ctx.send("🔄 Updating statistics. Please wait...")
            
            # Check for deleted channels first
            deleted_count = await bot.data_manager.check_and_remove_deleted_channels()
            
            # Updated message with progress
            await message.edit(content=f"🔄 Removed {deleted_count} deleted channels. Checking for new channels...")
            
            # Try to find any missing ticket channels
            new_count = 0
            guilds = bot.guilds
            for guild in guilds:
                for channel in guild.text_channels:
                    if "-" in channel.name:  # Simple check for ticket format
                        if channel.id not in bot.data_manager.ticket_channels:
                            bot.data_manager.ticket_channels[channel.id] = (channel.name, guild.id)
                            new_count += 1
            
            # Save data if any new channels found
            if new_count > 0:
                bot.data_manager.save_data()
            
            await message.edit(content=f"✅ Statistics updated!\n• Removed {deleted_count} deleted channels\n• Added {new_count} new channels\n• Total channels tracked: {len(bot.data_manager.ticket_channels)}")
            
        except Exception as e:
            await ctx.send(f"❌ Error updating statistics: {str(e)}")
            traceback.print_exc()


async def manage_user_command(bot, ctx, action: str, user: discord.User) -> None:
    """Handle the !manage_user command"""
    # Permission check - only administrator can manage user list
    if isinstance(ctx, discord.Interaction):
        if not ctx.user.guild_permissions.administrator:
            await ctx.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
    else:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ You need administrator permissions to use this command.")
            return
        
    tracked_users = bot.config.get("tracked_users", [])
    
    if action == "add":
        if user.id in tracked_users:
            message = f"⚠️ {user.name} is already being tracked."
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message(message, ephemeral=True)
            else:
                await ctx.send(message)
        else:
            tracked_users.append(user.id)
            bot.config["tracked_users"] = tracked_users
            bot.config_manager.save_config()
            message = f"✅ Added {user.name} to tracked users."
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message(message)
            else:
                await ctx.send(message)
    else:  # remove
        if user.id not in tracked_users:
            message = f"⚠️ {user.name} is not currently tracked."
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message(message, ephemeral=True)
            else:
                await ctx.send(message)
        else:
            tracked_users.remove(user.id)
            bot.config["tracked_users"] = tracked_users
            bot.config_manager.save_config()
            message = f"✅ Removed {user.name} from tracked users."
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message(message)
            else:
                await ctx.send(message)


async def cleanup_deleted_channels(bot, ctx) -> None:
    """Remove deleted channels from tracking"""
    if not bot.data_manager.ticket_channels:
        await ctx.send("No ticket channels are currently being tracked.")
        return
    
    # Create copy of dictionary to avoid size change during iteration errors
    channels_to_check = dict(bot.data_manager.ticket_channels)
    deleted_count = 0
    
    # Status check
    status_message = await ctx.send("🔍 Checking for deleted channels...")
    
    # Check each channel
    for channel_id, (name, guild_id) in channels_to_check.items():
        guild = bot.get_guild(guild_id)
        if not guild:
            # If server is inaccessible, skip
            continue
                
        channel = guild.get_channel(channel_id)
        if not channel:
            # Channel not found - remove from tracking
            if channel_id in bot.data_manager.ticket_channels:
                del bot.data_manager.ticket_channels[channel_id]
                deleted_count += 1
                
                # Also remove from recorded messages
                if channel_id in bot.data_manager.ticket_messages:
                    del bot.data_manager.ticket_messages[channel_id]
    
    # Save updated data
    if deleted_count > 0:
        bot.data_manager.save_data()
        bot.data_manager.save_messages()
        await status_message.edit(content=f"✅ Cleanup complete! Removed {deleted_count} deleted channel(s) from tracking.")
    else:
        await status_message.edit(content="✅ Cleanup complete! No deleted channels found.")