import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from utils.helpers import get_current_datetime_utc

def register_report_commands(bot):
    """Register report generation commands with the bot"""
    
    @bot.command(name="report", help="Generate activity report: !report [daily,weekly,monthly]")
    async def report_cmd(ctx, periods: str = None):
        if not periods:
            await ctx.send("❌ Error: Please specify period(s) (daily, weekly, or monthly).\nExample: `!report daily` or `!report daily,weekly`")
            return
                
        # Split periods if multiple are specified
        period_list = [p.strip().lower() for p in periods.split(',')]
        
        # Check that all specified periods are valid
        valid_periods = ["daily", "weekly", "monthly"]
        invalid_periods = [p for p in period_list if p not in valid_periods]
        
        if invalid_periods:
            await ctx.send(f"❌ Error: Invalid period(s): {', '.join(invalid_periods)}. Valid options are: daily, weekly, monthly.")
            return
                
        # Generate report for each specified period
        for period in period_list:
            try:
                await report_command(bot, ctx, period)
            except Exception as e:
                print(f"Error in report for period {period}: {e}")
                import traceback
                traceback.print_exc()
                await ctx.send(f"❌ Error generating report for {period} period: {str(e)}")
    
    @bot.command(name="forcereport", help="Force generate weekly report immediately")
    @discord.ext.commands.has_permissions(administrator=True)
    async def forcereport_cmd(ctx):
        try:
            await ctx.send("🔄 Generating forced weekly report...")
            await report_command(bot, ctx, "weekly")
        except Exception as e:
            print(f"Error in forcereport: {e}")
            import traceback
            traceback.print_exc()
            await ctx.send(f"❌ Error generating forced report: {str(e)}")
    
    @bot.command(name="urgentstats", help="Generate urgent statistics for all tracked users")
    async def urgentstats_cmd(ctx):
        try:
            await urgent_stats_command(bot, ctx)
        except Exception as e:
            print(f"Error in urgentstats: {e}")
            import traceback
            traceback.print_exc()
            await ctx.send(f"❌ Error generating urgent stats: {str(e)}")
    
    # New bi-weekly report command
    @bot.command(name="weeklyreport", help="Generate bi-weekly report (1-14 or 15-end of month)")
    async def weeklyreport_cmd(ctx):
        try:
            await ctx.send("🔄 Generating bi-weekly report...")
            await biweekly_report_command(bot, ctx)
        except Exception as e:
            print(f"Error in weeklyreport: {e}")
            import traceback
            traceback.print_exc()
            await ctx.send(f"❌ Error generating bi-weekly report: {str(e)}")
            

async def report_command(bot, ctx, period: str) -> None:
    """Handle the !report command with the specified period"""
    # Check and remove deleted channels
    await bot.data_manager.check_and_remove_deleted_channels()
    
    # Use datetime.now(timezone.utc) instead of deprecated utcnow()
    now = datetime.now(timezone.utc)
    
    if period == "daily":
        title = f"Daily Report ({now.strftime('%Y-%m-%d')})"
    elif period == "weekly":
        # Determine the current week period
        day = now.day
        if 1 <= day <= 7:
            period_str = "1-7"
        elif 8 <= day <= 14:
            period_str = "8-14"
        elif 15 <= day <= 21:
            period_str = "15-21"
        else:
            period_str = f"22-{_last_day_of_month(now.year, now.month)}"
        title = f"Weekly Report ({period_str} {now.strftime('%B')})"
    elif period == "monthly":
        title = f"Monthly Report ({now.strftime('%B %Y')})"
    else:
        message = "❌ Invalid period. Use 'daily', 'weekly', or 'monthly'."
        await ctx.send(message)
        return

    # Generate report content
    embed = discord.Embed(
        title=title,
        color=discord.Color.blue()
    )
    
    # Add current date and time in UTC in YYYY-MM-DD HH:MM:SS format
    current_utc = get_current_datetime_utc()
    embed.set_footer(text=f"Current UTC Time: {current_utc}")
    
    # If no data for period
    if period not in bot.data_manager.user_activity or not bot.data_manager.user_activity[period]:
        embed.description = "No activity recorded for this period."
        await ctx.send(embed=embed)
        return
    
    # Collect statistics for each user
    description = ""
    
    for user_id, activities in bot.data_manager.user_activity[period].items():
        if not any(len(channels) > 0 for channels in activities.values()):
            continue
            
        try:
            user = await bot.fetch_user(user_id)
            user_name = user.name
        except Exception:
            user_name = f"Unknown User"
        
        # Count number of channels for each action type
        addressed_count = len(activities.get("addressed", []))
        closed_count = len(activities.get("closed", []))
        deleted_count = len(activities.get("deleted", []))
        
        # Format string for each user
        if addressed_count > 0 or closed_count > 0 or deleted_count > 0:
            description += f"**{user_name}** (ID: {user_id})\n"
            description += f"• Tickets Addressed: **{addressed_count}**\n"
            description += f"• Tickets Closed: **{closed_count}**\n"
            description += f"• Tickets Deleted: **{deleted_count}**\n\n"
    
    if description:
        embed.description = description
    else:
        embed.description = "No activity recorded for this period."
        
    await ctx.send(embed=embed)


async def biweekly_report_command(bot, ctx) -> None:
    """Generate a report for either days 1-14 or days 15-end of month"""
    # Check and remove deleted channels
    await bot.data_manager.check_and_remove_deleted_channels()
    
    # Get current date
    now = datetime.now(timezone.utc)
    day = now.day
    
    # Determine the report period
    if 1 <= day <= 14:
        period_str = "1-14"
    else:
        last_day = _last_day_of_month(now.year, now.month)
        period_str = f"15-{last_day}"
    
    # Create report title
    title = f"Bi-Weekly Report ({period_str} {now.strftime('%B')})"
    
    # Use weekly data for our report
    period = "weekly"
    
    # Generate report content
    embed = discord.Embed(
        title=title,
        color=discord.Color.blue()
    )
    
    # Add current date and time in UTC
    current_utc = get_current_datetime_utc()
    embed.set_footer(text=f"Current UTC Time: {current_utc}")
    
    # If no data for period
    if period not in bot.data_manager.user_activity or not bot.data_manager.user_activity[period]:
        embed.description = "No activity recorded for this period."
        await ctx.send(embed=embed)
        return
    
    # Collect statistics for each user
    description = ""
    
    for user_id, activities in bot.data_manager.user_activity[period].items():
        if not any(len(channels) > 0 for channels in activities.values()):
            continue
            
        try:
            user = await bot.fetch_user(user_id)
            user_name = user.name
        except Exception:
            user_name = f"Unknown User"
        
        # Count number of channels for each action type
        addressed_count = len(activities.get("addressed", []))
        closed_count = len(activities.get("closed", []))
        deleted_count = len(activities.get("deleted", []))
        
        # Format string for each user
        if addressed_count > 0 or closed_count > 0 or deleted_count > 0:
            description += f"**{user_name}** (ID: {user_id})\n"
            description += f"• Tickets Addressed: **{addressed_count}**\n"
            description += f"• Tickets Closed: **{closed_count}**\n"
            description += f"• Tickets Deleted: **{deleted_count}**\n\n"
    
    if description:
        embed.description = description
    else:
        embed.description = "No activity recorded for this period."
        
    await ctx.send(embed=embed)


async def urgent_stats_command(bot, ctx) -> None:
    """Handle the !urgentstats command - shows stats for all periods and all users"""
    # Check and remove deleted channels
    await bot.data_manager.check_and_remove_deleted_channels()
    
    # Get list of tracked users
    tracked_users = bot.config.get("tracked_users", [])
    if not tracked_users:
        await ctx.send("No users are currently being tracked.")
        return
    
    # Create embed
    embed = discord.Embed(
        title="🚨 Urgent Statistics Report",
        description="Statistics for all tracked users across all time periods",
        color=discord.Color.red()
    )
    
    # Add current date and time in UTC in YYYY-MM-DD HH:MM:SS format
    current_utc = get_current_datetime_utc()
    embed.set_footer(text=f"Current UTC Time: {current_utc}")
    
    # Add statistics for each user
    for user_id in tracked_users:
        try:
            user = await bot.fetch_user(user_id)
            user_name = user.name
        except Exception:
            user_name = f"Unknown User (ID: {user_id})"
        
        # Collect statistics for all periods
        stats_text = ""
        
        for period in ["daily", "weekly", "monthly"]:
            activities = bot.data_manager.user_activity.get(period, {}).get(user_id, {})
            if not activities:
                continue
            
            addressed_count = len(activities.get("addressed", []))
            closed_count = len(activities.get("closed", []))
            deleted_count = len(activities.get("deleted", []))
            
            if addressed_count > 0 or closed_count > 0 or deleted_count > 0:
                stats_text += f"**{period.capitalize()}**: "
                stats_text += f"Addressed: {addressed_count}, "
                stats_text += f"Closed: {closed_count}, "
                stats_text += f"Deleted: {deleted_count}\n"
        
        if stats_text:
            embed.add_field(
                name=f"{user_name} (ID: {user_id})",
                value=stats_text,
                inline=False
            )
    
    if len(embed.fields) == 0:
        embed.description = "No activity recorded for any user in any period."
        
    await ctx.send(embed=embed)


def _last_day_of_month(year: int, month: int) -> int:
    """Get the last day of the month"""
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    return (next_month - timedelta(days=1)).day