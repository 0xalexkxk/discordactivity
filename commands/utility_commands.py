import discord
from discord.ext import commands
from datetime import datetime, timezone
from utils.ui import TicketListPaginator
from utils.helpers import get_current_datetime_utc

def register_utility_commands(bot):
    """Register utility commands with the bot"""
    
    @bot.command(name="help", help="Show available commands")
    async def help_cmd(ctx):
        embed = discord.Embed(
            title="Ticket Tracker - Help",
            description="Here are the available commands:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="!report [period]", 
            value="Generate activity report for all users for the specified period.\n" +
                  "Period can be: 'daily', 'weekly', 'monthly', or combined like 'daily,weekly'", 
            inline=False
        )
        embed.add_field(
            name="!forcereport", 
            value="Force generate weekly report immediately", 
            inline=False
        )
        embed.add_field(
            name="!urgentstats", 
            value="Generate detailed statistics report for all tracked users", 
            inline=False
        )
        embed.add_field(
            name="!list_users", 
            value="List all users being tracked for ticket activity", 
            inline=False
        )
        embed.add_field(
            name="!list_tickets", 
            value="List all tracked ticket channels with links", 
            inline=False
        )
        embed.add_field(
            name="!list_sahara_bots", 
            value="List all tracked Sahara bot IDs", 
            inline=False
        )
        embed.add_field(
            name="!manage_user [add/remove] @user", 
            value="Add or remove a user from tracking (Admin only)", 
            inline=False
        )
        embed.add_field(
            name="!add_user [user_id]", 
            value="Add a user by ID to tracking (Admin only)", 
            inline=False
        )
        embed.add_field(
            name="!add_channel [link or ID]", 
            value="Add existing channel to tracking (Admin only)", 
            inline=False
        )
        embed.add_field(
            name="!bulk_add_channels [link1] [link2] ...", 
            value="Add multiple channels to tracking (Admin only)", 
            inline=False
        )
        embed.add_field(
            name="!set_reports_channel [channel_id]", 
            value="Set channel for automatic reports (Admin only)", 
            inline=False
        )
        embed.add_field(
            name="!update_stats", 
            value="Update all statistics (Admin only)", 
            inline=False
        )
        embed.add_field(
            name="!debug [on/off]",
            value="Toggle debug mode (Admin only)",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @bot.command(name="list_users", help="List all users being tracked for ticket activity")
    async def list_users_cmd(ctx):
        await list_users_command(bot, ctx)
    
    @bot.command(name="list_tickets", help="List all tracked ticket channels")
    async def list_tickets_cmd(ctx):
        await list_tickets_command(bot, ctx)
    
    @bot.command(name="list_sahara_bots", help="List all tracked Sahara bot IDs")
    async def list_sahara_bots_cmd(ctx):
        sahara_bot_ids = bot.config.get("sahara_bot_ids", [])
        
        if not sahara_bot_ids:
            await ctx.send("No Sahara bot IDs are currently being tracked.")
            return
            
        embed = discord.Embed(
            title="Tracked Sahara Bots",
            description="Bot IDs currently being monitored for ticket activity:",
            color=discord.Color.green()
        )
        
        for bot_id in sahara_bot_ids:
            try:
                bot_user = await bot.fetch_user(bot_id)
                embed.add_field(name=bot_user.name, value=f"ID: {bot_id}", inline=True)
            except Exception as e:
                embed.add_field(name=f"Unknown Bot", value=f"ID: {bot_id}\nError: {str(e)}", inline=True)
        
        await ctx.send(embed=embed)


async def list_users_command(bot, ctx) -> None:
    """Handle the !list_users command"""
    tracked_users = bot.config.get("tracked_users", [])
    
    if not tracked_users:
        await ctx.send("No users are currently being tracked.")
        return
        
    embed = discord.Embed(
        title="Tracked Users",
        description="Users currently being tracked for ticket activity:",
        color=discord.Color.green()
    )
    
    for user_id in tracked_users:
        try:
            user = await bot.fetch_user(user_id)
            embed.add_field(name=user.name, value=f"ID: {user.id}", inline=True)
        except Exception as e:
            embed.add_field(name=f"Invalid User ID", value=f"ID: {user_id}\nUse `!remove_user_id {user_id}` to remove", inline=True)
    
    current_utc = get_current_datetime_utc()
    embed.set_footer(text=f"Current UTC Time: {current_utc}")
        
    await ctx.send(embed=embed)


async def list_tickets_command(bot, ctx) -> None:
    """Handle the !list_tickets command with interactive pagination"""
    # First check for deleted channels
    updated = await bot.data_manager.check_and_remove_deleted_channels()
    
    if not bot.data_manager.ticket_channels:
        await ctx.send("No ticket channels are currently being tracked.")
        return
    
    # Count total number of channels
    total_channels = len(bot.data_manager.ticket_channels)
    status_msg = await ctx.send(f"📋 Found **{total_channels}** tracked ticket channels. Preparing pagination view...")
    
    # Prepare flat list of channels
    channels = []
    for channel_id, (name, guild_id) in bot.data_manager.ticket_channels.items():
        channels.append((channel_id, name, guild_id))
    
    # Sort channels by name
    channels.sort(key=lambda x: x[1])
    
    # Create paginator object
    paginator = TicketListPaginator(ctx, channels, bot, updated)
    
    # Start the paginator
    await paginator.start()
    await status_msg.delete()