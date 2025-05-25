import discord
from bot import TicketBot

if __name__ == "__main__":
    # Create and start the bot
    bot = TicketBot()
    
    # Replace with your real token
    token = "MTM2MzU2NjY3MDI0NDc0MTMxMg.GPxdcy.eTjFT7W2uVhBfF9Fb-3LF7z62HkWkI3paXBA58"
    
    if not token:
        print("Error: Please provide a valid Discord token")
        exit(1)
    
    bot.run(token)