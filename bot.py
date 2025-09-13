import discord
from openai import OpenAI
import os

# --- Simple in-memory state: per-channel participants + short history ---
STATE = {"channels": {}}  # {channel_id: {"order":[uid,uid], "participants":{uid: display}, "history":[{"role","content"}]} }
MAX_HISTORY = 30  # keep last N messages in context (user+assistant)

def _chan_state(cid: int):
    st = STATE["channels"].get(cid)
    if not st:
        st = {"order": [], "participants": {}, "history": []}
        STATE["channels"][cid] = st
    return st

def _register_participant(st, user_id: int, display: str):
    uid = str(user_id)
    if uid in st["participants"]:
        st["participants"][uid] = display  # update display if changed
        return
    if len(st["order"]) < 2:
        st["order"].append(uid)
        st["participants"][uid] = display
    # if already have 2, ignore extra users (your use-case is 2 people)

def _roster_text(st):
    names = [st["participants"][uid] for uid in st["order"] if uid in st["participants"]]
    return ", ".join(names) if names else "(awaiting two participants)"

def _system_prompt(st):
    return (
        "You are facilitating a two-person roleplay in this Discord channel.\n"
        "Rules:\n"
        "• Keep strict continuity of places/characters/items mentioned earlier in THIS channel.\n"
        "• User messages are prefixed as 'Name: ...'. Do NOT speak for those names; narrate as world/NPCs and outcomes only.\n"
        "• Keep replies concise unless more detail is clearly needed.\n"
        f"Participants: {_roster_text(st)}"
    )

def _trim_history(st):
    if len(st["history"]) > MAX_HISTORY:
        st["history"] = st["history"][-MAX_HISTORY:]

# --- Discord client setup ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Debug prints (optional, remove later)
print("DEBUG: SHAPES_API_KEY value is:", os.getenv("SHAPES_API_KEY"))
print("DEBUG: DISCORD_BOT_TOKEN value is:", os.getenv("DISCORD_BOT_TOKEN"))
print("DEBUG: CHANNEL_ID value is:", os.getenv("CHANNEL_ID"))

# Shapes (OpenAI-compatible)
shapes_client = OpenAI(
    api_key=os.getenv("SHAPES_API_KEY"),
    base_url="https://api.shapes.inc/v1/"
)
shape_model = os.getenv("SHAPE_MODEL")  # e.g., "shapesinc/nisa-fsq0"

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

    st = _chan_state(message.channel.id)
    _register_participant(st, message.author.id, message.author.display_name)

    # Prefix with speaker so the model can attribute lines
    speaker = st["participants"].get(str(message.author.id), message.author.display_name)
    user_line = f"{speaker}: {message.content}"

    try:
        # Append the new user line to rolling history
        st["history"].append({"role": "user", "content": user_line})
        _trim_history(st)

        # Build messages = system + rolling history
        messages = [{"role": "system", "content": _system_prompt(st)}]
        messages.extend(st["history"])

        # Call the model
        response = shapes_client.chat.completions.create(
            model=shape_model,
            messages=messages
        )

        # Get the AI response
        ai_reply = response.choices[0].message.content or ""

        # Save assistant reply for continuity
        st["history"].append({"role": "assistant", "content": ai_reply})
        _trim_history(st)

        # Split and send in chunks if over 2000 chars
        max_length = 2000
        text = ai_reply
        while len(text) > 0:
            chunk = text[:max_length]
            text = text[max_length:]
            await message.channel.send(chunk)

    except Exception as e:
        error_msg = f"Error getting response: {str(e)[:100]}... Try again later."
        await message.channel.send(error_msg)

# Run the bot
client.run(os.getenv("DISCORD_BOT_TOKEN"))
