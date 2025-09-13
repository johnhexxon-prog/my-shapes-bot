import os
import re
import discord
from openai import OpenAI

# ---- Discord setup ----
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ---- Shapes (OpenAI-compatible) client ----
shapes_client = OpenAI(
    api_key=os.getenv("SHAPES_API_KEY"),
    base_url="https://api.shapes.inc/v1/",
)
shape_model = os.getenv("SHAPE_MODEL")  # e.g., "shapesinc/nisa-fsq0"

CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

DISCORD_LIMIT = 2000  # hard limit
SAFE_TEXT_LIMIT = 2000
# For code blocks we need to reserve wrapper overhead: ```{lang}\n ... \n```
def _code_wrapper_overhead(lang: str) -> int:
    return 8 + len(lang)  # 3 backticks + lang + '\n' + '\n' + 3 backticks

def _split_plain(text: str, limit: int):
    chunks = []
    buf = ""
    for para in text.splitlines(keepends=True):
        # If a single line exceeds limit, split by spaces, then hard-cut
        while len(para) > limit:
            cut = para.rfind(" ", 0, limit)
            if cut <= 0:
                cut = limit
            chunks.append((buf + para[:cut]) if buf else para[:cut])
            buf = ""
            para = para[cut:].lstrip()
        candidate = (buf + para) if buf else para
        if len(candidate) <= limit:
            buf = candidate
        else:
            if buf:
                chunks.append(buf)
            buf = para
    if buf:
        chunks.append(buf)
    return [c.rstrip("\n") for c in chunks]

def _split_code(code: str, lang: str, limit: int):
    wrap_overhead = _code_wrapper_overhead(lang)
    inner_limit = max(1, limit - wrap_overhead)
    raw_chunks = _split_plain(code, inner_limit)
    return [f"```{lang}\n{c}\n```" for c in raw_chunks]

def split_for_discord(message: str, limit: int = DISCORD_LIMIT):
    """
    Splits message into <=limit chunks. Preserves code fences across chunks.
    Supports fenced blocks like ```lang\n...\n```.
    """
    chunks = []
    # Find fenced code blocks and split around them
    pattern = re.compile(r"```([^\n`]*)\n([\s\S]*?)```", re.MULTILINE)
    pos = 0
    for m in pattern.finditer(message):
        pre = message[pos:m.start()]
        lang = (m.group(1) or "").strip()
        code = m.group(2)
        # split pre as plain text
        if pre:
            chunks.extend(_split_plain(pre, limit))
        # split code with wrappers
        chunks.extend(_split_code(code, lang, limit))
        pos = m.end()
    tail = message[pos:]
    if tail:
        chunks.extend(_split_plain(tail, limit))
    # Final safety: if anything still exceeds limit, hard-cut
    fixed = []
    for c in chunks:
        if len(c) <= limit:
            fixed.append(c)
        else:
            for i in range(0, len(c), limit):
                fixed.append(c[i:i+limit])
    # Drop empty pieces
    return [c for c in fixed if c.strip() != ""]

@client.event
async def on_ready():
    print(f'Bot logged in as {client.user}')

@client.event
async def on_message(message: discord.Message):
    if message.channel.id != CHANNEL_ID:
        return
    if message.author == client.user:
        return

    user_message = message.content

    try:
        response = shapes_client.chat.completions.create(
            model=shape_model,
            messages=[{"role": "user", "content": user_message}],
        )
        ai_reply = response.choices[0].message.content or ""

        for part in split_for_discord(ai_reply, DISCORD_LIMIT):
            await message.channel.send(part)

    except Exception as e:
        error_msg = f"Error getting response: {str(e)[:300]}"
        for part in split_for_discord(error_msg, DISCORD_LIMIT):
            await message.channel.send(part)

client.run(os.getenv("DISCORD_BOT_TOKEN"))
