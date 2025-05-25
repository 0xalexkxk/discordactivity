from discord.ext import tasks
from datetime import datetime, timezone, timedelta

def setup_scheduled_tasks(bot):
    """Set up all scheduled tasks for the bot"""
    
    @tasks.loop(minutes=1)
    async def reset_daily_activity():
        """Reset daily activity at midnight"""
        now = datetime.now(timezone.utc)
        if now.hour == 0 and now.minute == 0:
            bot.data_manager.user_activity["daily"] = {}
            print(f"[{now}] Daily activity counters reset.")
            bot.data_manager.save_data()

    @tasks.loop(minutes=1)
    async def check_weekly_reset():
        """Check if weekly activity should be reset"""
        now = datetime.now(timezone.utc)
        # Reset weekly counters on the 1st, 8th, 15th, and 22nd of each month
        if now.hour == 0 and now.minute == 0:
            if now.day in [1, 8, 15, 22]:
                bot.data_manager.user_activity["weekly"] = {}
                print(f"[{now}] Weekly activity counters reset.")
                bot.data_manager.save_data()

    @tasks.loop(minutes=1)
    async def check_monthly_reset():
        """Check if monthly activity should be reset"""
        now = datetime.now(timezone.utc)
        # Reset monthly counters on the 1st of each month
        if now.hour == 0 and now.minute == 0 and now.day == 1:
            bot.data_manager.user_activity["monthly"] = {}
            print(f"[{now}] Monthly activity counters reset.")
            bot.data_manager.save_data()

    @tasks.loop(hours=12)
    async def check_deleted_channels():
        """Periodically check for deleted channels and remove them from tracking"""
        if not bot.data_manager.ticket_channels:
            return
            
        print(f"[{datetime.now(timezone.utc)}] Checking for deleted channels...")
        
        deleted_count = await bot.data_manager.check_and_remove_deleted_channels()
        
        if deleted_count > 0:
            print(f"[{datetime.now(timezone.utc)}] Removed {deleted_count} deleted channel(s) from tracking.")

    @tasks.loop(hours=1)
    async def check_sahara_bots():
        """Periodically check Sahara Bots configuration"""
        await bot.config_manager.check_sahara_bots()

    @tasks.loop(minutes=1)
    async def send_automated_reports():
        """Send automated reports on specific days at 00:00 UTC"""
        now = datetime.now(timezone.utc)
        
        # Check if it's time to send a report (00:00 on 7th, 14th, 21st, or 28th)
        if now.hour == 0 and now.minute == 0 and now.day in [7, 14, 21, 28]:
            print(f"[{now}] Time to send automated weekly report.")
            
            # Check if reports channel is set
            reports_channel_id = bot.config.get("reports_channel_id")
            if not reports_channel_id:
                print("No reports channel set. Skipping automated report.")
                return
                
            channel = bot.get_channel(reports_channel_id)
            if not channel:
                print(f"Could not find channel with ID {reports_channel_id}. Skipping automated report.")
                return
                
            try:
                # Generate and send the weekly report
                from commands.report_commands import report_command
                
                await channel.send("📊 **Automated Weekly Report**")
                await report_command(bot, channel, "weekly")
                print(f"[{now}] Automated weekly report sent to channel {channel.name} (ID: {channel.id})")
            except Exception as e:
                print(f"Error sending automated report: {e}")
                import traceback
                traceback.print_exc()

    # Start all the tasks
    reset_daily_activity.start()
    check_weekly_reset.start()
    check_monthly_reset.start()
    check_deleted_channels.start()
    check_sahara_bots.start()
    send_automated_reports.start()
    
    # Setup pre-loop hooks for all tasks
    @reset_daily_activity.before_loop
    @check_weekly_reset.before_loop
    @check_monthly_reset.before_loop
    @check_deleted_channels.before_loop
    @check_sahara_bots.before_loop
    @send_automated_reports.before_loop
    async def before_tasks():
        """Wait until the bot is ready before starting tasks"""
        await bot.wait_until_ready()
    
    # Return tasks for reference
    return {
        "reset_daily_activity": reset_daily_activity,
        "check_weekly_reset": check_weekly_reset,
        "check_monthly_reset": check_monthly_reset,
        "check_deleted_channels": check_deleted_channels,
        "check_sahara_bots": check_sahara_bots,
        "send_automated_reports": send_automated_reports
    }