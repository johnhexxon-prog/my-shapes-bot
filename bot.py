import discord
from openai import OpenAI
import os  # This is new—for env vars

# Set up Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Set up Shapes API client (OpenAI-compatible)
shapes_client = OpenAI(
    api_key=os.getenv("SHAPES_API_KEY"),  # Pulls from Railway env var
    base_url="https://api.shapes.inc/v1/"
)
shape_model = "shapesinc/nisa-fsq0"  # Replace ONLY this with your actual shape username, e.g., shapesinc/mybot

# Specify the channel ID where the bot should respond
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # Pulls from Railway env var (convert to int since IDs are numbers)

@client.event
async def on_ready():
    print(f'Bot logged in as {client.user}')

@client.event
async def on_message(message):
    # Only respond in the specific channel
    if message.channel.id != CHANNEL_ID:
        return
    
    if message.author == client.user:
        return  # Ignore own messages
    
    # Respond to all messages in this channel (no prefix needed)
    user_message = message.content
    
    # Send to Shapes API
    response = shapes_client.chat.completions.create(
        model=shape_model,
        messages=[{"role": "user", "content": user_message}]
    )
    
    # Get the AI response
    ai_reply = response.choices[0].message.content
    
    # Send back to Discord
    await message.channel.send(ai_reply)

# Run the bot
client.run(os.getenv("DISCORD_BOT_TOKEN"))  # Pulls from Railway env var