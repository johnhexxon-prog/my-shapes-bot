import os
import re
from collections import defaultdict, deque

import discord
from openai import OpenAI

# ---- Discord constants ----
MAX_DISCORD_LEN = 2000                      # Discord API hard cap per message
RP_CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # the shared/group RP channel ID

# ---- Discord client ----
intents = discord.Intents.default()
intents.message_content = True   # enable in Developer Portal
intents.members = True           # for reliable display_name/nickname
client = discord.Client(intents=intents)

# ---- Debug (optional; remove in prod) ----
print("DEBUG: SHAPES_API_KEY value is:", os.getenv("SHAPES_API_KEY"))
print("DEBUG: DISCORD_BOT_TOKEN value is:", os.getenv("DISCORD_BOT_TOKEN"))
print("DEBUG: CHANNEL_ID value is:", os.getenv("CHANNEL_ID"))

# ---- Shapes (OpenAI-compatible) client ----
shapes_client = OpenAI(
    api_key=os.getenv("SHAPES_API_KEY"),
    base_url="https://api.shapes.inc/v1/"
)
shape_model = os.getenv("SHAPE_MODEL")  # e.g., "shapesinc/nisa-fsq0"

# ---- In-memory state ----
# One rolling transcript per channel with speaker tags. Keep it short to control prompt size.
# Each entry looks like: "[user @Alice|123]: hi" or "[assistant @Bot|999]: hello"
CHANNEL_TRANSCRIPTS: dict[int, deque[str]] = defaultdict(lambda: deque(maxlen=30))

# ---------------- Utilities ----------------
def _needs_reopen(prev_chunk: str) -> bool:
    """Return True if we ended inside a triple backtick code block."""
    fences = len(re.findall(r"(?<!`)```", prev_chunk))
    return fences % 2 == 1

def split_for_discord(text: str, limit: int = MAX_DISCORD_LEN) -> list[str]:
    """
    Split text into chunks <= limit, preferring newlines/spaces.
    If a split occurs inside a ``` code block, close it at the end of the chunk
    and reopen it at the start of the next chunk to preserve formatting.
    """
    chunks: list[str] = []
    remainder = text
    reopen_prefix = ""  # set to "```\n" if we split inside a code block

    while len(remainder) > limit:
        budget = limit - len(reopen_prefix)
        slice_ = remainder[:budget]

        split_at = slice_.rfind("\n")
        if split_at == -1:
            split_at = slice_.rfind(" ")
            if split_at == -1:
                split_at = budget

        chunk = reopen_prefix + remainder[:split_at]
        chunk = chunk.rstrip()

        if _needs_reopen(chunk):
            closing = "\n```"
            if len(chunk) + len(closing) > limit:
                chunk = chunk[:limit - len(closing)]
            chunk += closing
            reopen_prefix = "```\n"
        else:
            reopen_prefix = ""

        chunks.append(chunk)
        remainder = remainder[split_at:].lstrip()

    if remainder:
        final_chunk = reopen_prefix + remainder
        while len(final_chunk) > limit:
            chunks.append(final_chunk[:limit])
            final_chunk = final_chunk[limit:]
        if final_chunk:
            chunks.append(final_chunk)

    return [c for c in chunks if c]

def display_name(user: discord.abc.User) -> str:
    if isinstance(user, discord.Member):
        return user.display_name or user.name
    return user.name

def speaker_tag(user: discord.abc.User) -> str:
    # Stable tag the model can track
    return f"@{display_name(user)}|{user.id}"

def format_user_line(msg: discord.Message) -> str:
    return f"[user {speaker_tag(msg.author)}]: {msg.content}"

def format_bot_line(bot_user: discord.ClientUser, text: str) -> str:
    return f"[assistant {speaker_tag(bot_user)}]: {text}"

def build_group_messages(channel_id: int, latest_user_line: str) -> list[dict]:
    """
    Build the prompt for Shapes/OpenAI:
      - system: multi-user RP rules
      - user: short labeled transcript (recent history + the newest user line)
    """
    transcript = CHANNEL_TRANSCRIPTS[channel_id]
    joined = "\n".join([*transcript, latest_user_line])

    system = (
        "You are {shape}, roleplaying in a multi-user Discord channel. "
        "Each line is labeled with a speaker tag like [user @Name|id]: or [assistant @Bot|id]: . "
        "Use the tags to know who is speaking and address them appropriately. "
        "Do NOT write dialogue or actions for users. "
        "Keep replies concise and under ~1800 characters to fit Discord limits. "
        "If several users spoke, you may address more than one, but never invent their lines."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": joined},
    ]

# ---------------- Events ----------------
@client.event
async def on_ready():
    print(f'Bot logged in as {client.user}')

@client.event
async def on_message(message: discord.Message):
    # Only operate in the configured group RP channel
    if message.channel.id != RP_CHANNEL_ID:
        return

    # Ignore our own messages (we add them to transcript manually after sending)
    if message.author == client.user:
        return

    # (Optional) Ignore other bots to avoid bot-bot loops
    if getattr(message.author, "bot", False):
        return

    # Build the labeled line for the incoming human message
    latest_user_line = format_user_line(message)

    try:
        # Build prompt using current channel transcript + the new user line (not yet appended)
        msgs = build_group_messages(message.channel.id, latest_user_line)

        # Call Shapes API
        response = shapes_client.chat.completions.create(
            model=shape_model,
            messages=msgs
        )
        ai_reply = (response.choices[0].message.content or "").strip()
        if not ai_reply:
            await message.channel.send("I didn’t get a reply from the model. Try again.")
            return

        # Update transcript: append the new user line, then the assistant line
        CHANNEL_TRANSCRIPTS[message.channel.id].append(latest_user_line)
        CHANNEL_TRANSCRIPTS[message.channel.id].append(format_bot_line(client.user, ai_reply))

        # Send safely under Discord's limit
        chunks = split_for_discord(ai_reply, MAX_DISCORD_LEN)
        total = len(chunks)
        for i, chunk in enumerate(chunks, start=1):
            suffix = f" *(part {i}/{total})*" if total > 1 else ""
            if len(chunk) + len(suffix) > MAX_DISCORD_LEN:
                chunk = chunk[:MAX_DISCORD_LEN - len(suffix)]
            await message.channel.send(chunk + suffix)

    except Exception as e:
        # Keep error messages short
        msg = f"Error getting response: {str(e)[:300]}"
        await message.channel.send(msg)

# Run the bot
client.run(os.getenv("DISCORD_BOT_TOKEN"))
