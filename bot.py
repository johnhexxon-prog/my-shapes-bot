import discord
from openai import OpenAI
import os

# Set up Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Debug prints (optional, remove later)
print("DEBUG: SHAPES_API_KEY value is:", os.getenv("SHAPES_API_KEY"))
print("DEBUG: DISCORD_BOT_TOKEN value is:", os.getenv("DISCORD_BOT_TOKEN"))
print("DEBUG: CHANNEL_ID value is:", os.getenv("CHANNEL_ID"))

# Set up Shapes API client (OpenAI-compatible)
shapes_client = OpenAI(
    api_key=os.getenv("SHAPES_API_KEY"),
    base_url="https://api.shapes.inc/v1/"
)
shape_model = os.getenv("SHAPE_MODEL")  # Pulls from env var, e.g., "shapesinc/nisa-fsq0"

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

    try:
        # Send to Shapes API with error handling
        response = shapes_client.chat.completions.create(
            model=shape_model,
            messages=[{"role": "user", "content": user_message}]
        )

        # Get the AI response
        ai_reply = response.choices[0].message.content

        # Split and send in chunks if over 2000 chars
        max_length = 2000
        while len(ai_reply) > 0:
            chunk = ai_reply[:max_length]
            ai_reply = ai_reply[max_length:]
            await message.channel.send(chunk)

    except Exception as e:
        # Fallback if API fails (e.g., network error, rate limit)
        error_msg = f"Error getting response: {str(e)[:100]}... Try again later."
        await message.channel.send(error_msg)

# Run the bot
client.run(os.getenv("DISCORD_BOT_TOKEN"))