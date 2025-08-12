import discord
from openai import OpenAI

# Set up Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Set up Shapes API client (OpenAI-compatible)
shapes_client = OpenAI(
    api_key="ZTHZ8V0FC3N06E6415DSVUDGUTI416VQHHDUSVMXTUK",  # Paste your Shapes API key here
    base_url="https://api.shapes.inc/v1/"
)
shape_model = "shapesinc/nisa-fsq0"  # Replace with your actual shape's username, e.g., shapesinc/mybot

# Specify the channel ID where the bot should respond (get this from Discord: right-click channel > Copy ID; enable Developer Mode in settings if needed)
CHANNEL_ID = 123456789012345678  # Replace with your actual channel ID (it's a big number)

@client.event
async def on_ready():
    print(f'Bot logged in as {client.user}')

@client.event
async def on_message(message):
    # Only respond in the specific channel
    if message.channel.id != 1051244799279255683:
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
client.run("MTQwNDgyMDE2NzI0MjAyMzA0NA.Gh_jh_.lruQReqcmaJB4kV3y9cbPRVnBYPwN86NisMcFc")  # Paste your Discord bot token here