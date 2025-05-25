import discord
from datetime import datetime, timezone

class TicketListPaginator:
    def __init__(self, ctx, channels, bot, updated_count=0):
        self.ctx = ctx
        self.bot = bot
        self.channels = channels
        self.updated_count = updated_count
        
        # Pagination settings
        self.channels_per_page = 10
        self.current_page = 0
        self.total_pages = (len(channels) + self.channels_per_page - 1) // self.channels_per_page
        
        # Split channels into pages
        self.pages = [
            channels[i:i+self.channels_per_page] 
            for i in range(0, len(channels), self.channels_per_page)
        ]
        
        self.message = None
    
    def get_embed(self):
        """Create embed for current page"""
        current_page_channels = self.pages[self.current_page]
        
        embed = discord.Embed(
            title=f"Tracked Tickets",
            description=f"Page {self.current_page+1}/{self.total_pages}",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        channel_list = ""
        for channel_id, name, guild_id in current_page_channels:
            channel_url = f"https://discord.com/channels/{guild_id}/{channel_id}"
            channel_list += f"• [{name}]({channel_url})\n"
        
        embed.add_field(name=f"Channels {self.current_page*self.channels_per_page+1}-{self.current_page*self.channels_per_page+len(current_page_channels)}", 
                       value=channel_list, inline=False)
        
        # Add general information
        embed.set_footer(text=f"Total: {len(self.channels)} channels" + 
                        (f" • {self.updated_count} deleted channel(s) removed" if self.updated_count else ""))
        
        return embed
    
    async def start(self):
        """Start the pagination"""
        # Create initial view with buttons
        view = self.get_navigation_view()
        
        # Send initial message with buttons
        self.message = await self.ctx.send(embed=self.get_embed(), view=view)
    
    def get_navigation_view(self):
        """Create navigation buttons view"""
        view = discord.ui.View(timeout=90)  # Timeout after 90 seconds
        
        # Previous page button
        prev_page = discord.ui.Button(
            label="◀ Previous Page", 
            style=discord.ButtonStyle.primary,
            disabled=self.current_page == 0
        )
        prev_page.callback = self.prev_page_callback
        view.add_item(prev_page)
        
        # Page indicator (not a button, just for info)
        page_indicator = discord.ui.Button(
            label=f"Page {self.current_page+1}/{self.total_pages}", 
            style=discord.ButtonStyle.secondary,
            disabled=True
        )
        view.add_item(page_indicator)
        
        # Next page button
        next_page = discord.ui.Button(
            label="Next Page ▶", 
            style=discord.ButtonStyle.primary,
            disabled=self.current_page >= len(self.pages) - 1
        )
        next_page.callback = self.next_page_callback
        view.add_item(next_page)
        
        # Add a timeout callback
        async def on_timeout():
            # Disable all buttons after timeout
            for item in view.children:
                item.disabled = True
            await self.message.edit(view=view)
        
        view.on_timeout = on_timeout
        return view
    
    async def prev_page_callback(self, interaction):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self.get_navigation_view())
    
    async def next_page_callback(self, interaction):
        """Go to next page"""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self.get_navigation_view())