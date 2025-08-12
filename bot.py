import discord
from openai import OpenAI
import os

# Set up Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Set up Shapes API client (OpenAI-compatible)
shapes_client = OpenAI(
    api_key=os.getenv("SHAPES_API_KEY"),
    base_url="https://api.shapes.inc/v1/"
)
shape_model = "shapesinc/your-shape-username"  # Replace with your actual shape username

# Specify the channel ID where the bot should respond
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

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
    
    # Prepend user's name to the message for the AI to distinguish
    user_message = f"{message.author.name}: {message.content}"
    
    try:
        # Send to Shapes API with per-user context header
        response = shapes_client.chat.completions.create(
            model=shape_model,
            messages=[{"role": "user", "content": user_message}],
            extra_headers={"X-User-Id": str(message.author.id)}  # Maintains separate context per user
        )
        
        # Get the AI response and truncate if too long (Discord limit: 2000 chars)
        ai_reply = response.choices[0].message.content
        if len(ai_reply) > 1990:
            ai_reply = ai_reply[:1990] + "... (truncated)"
        
        # Send back to Discord
        await message.channel.send(ai_reply)
    except Exception as e:
        # Fallback error message
        await message.channel.send(f"Error: {str(e)[:100]}... Try again!")

# Run the bot
client.run(os.getenv("DISCORD_BOT_TOKEN"))