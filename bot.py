import discord
from openai import OpenAI
import os

# Set up Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Debug print for API key
print("DEBUG: SHAPES_API_KEY value is:", os.getenv("SHAPES_API_KEY"))

# Set up Shapes API client (OpenAI-compatible)
shapes_client = OpenAI(
    api_key=os.getenv("SHAPES_API_KEY"),
    base_url="https://api.shapes.inc/v1/"
)
shape_model = "shapesinc/your-shape-username"  # Your actual value here

# Specify the channel ID where the bot should respond
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

@client.event
async def on_ready():
    print(f'Bot logged in as {client.user}')

@client.event
async def on_message(message):
    if message.channel.id != CHANNEL_ID:
        return
    
    if message.author == client.user:
        return
    
    user_message = message.content
    
    response = shapes_client.chat.completions.create(
        model=shape_model,
        messages=[{"role": "user", "content": user_message}]
    )
    
    ai_reply = response.choices[0].message.content
    
    await message.channel.send(ai_reply)

# Run the bot
client.run(os.getenv("DISCORD_BOT_TOKEN"))