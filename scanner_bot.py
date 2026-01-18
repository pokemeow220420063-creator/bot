import os
import discord
from discord.ext import commands
import json
from threading import Thread
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

# --- PHẦN FAKE WEB ĐỂ CHẠY 24/7 ---
app = Flask('')

@app.route('/')
def home():
    return "Hello World! Scanner Bot is Running 24/7."

def run_web():
    # Railway sẽ cấp một cổng (PORT) tự động, ta cần lấy nó
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()
# ----------------------------------

# --- PHẦN BOT ---
TOKEN = os.getenv("TOKEN")
POKEMEOW_ID = 664508672713424926 

intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix=";", intents=intents)

# (Giữ nguyên hàm parse_to_dict và lệnh ;l như cũ)
def parse_to_dict(msg):
    data = {"id": msg.id, "content": msg.content, "embeds": [], "components": []}
    for emb in msg.embeds:
        data["embeds"].append({
            "author": emb.author.name if emb.author else None,
            "title": emb.title, "description": emb.description,
            "footer": emb.footer.text if emb.footer else None,
        })
    for row in msg.components:
        for comp in row.children:
            if isinstance(comp, discord.Button):
                data["components"].append({
                    "label": comp.label, "custom_id": comp.custom_id,
                    "emoji": str(comp.emoji) if comp.emoji else None
                })
    return data

@bot.command(name="l")
async def latest_data(ctx, amount: int = 1):
    found_count = 0
    async for message in ctx.channel.history(limit=50):
        if message.author.id == POKEMEOW_ID:
            found_count += 1
            raw_data = parse_to_dict(message)
            json_str = json.dumps(raw_data, ensure_ascii=False, indent=2)
            if len(json_str) > 1900:
                with open("temp.json", "w", encoding="utf-8") as f: f.write(json_str)
                await ctx.send(file=discord.File("temp.json"))
            else:
                await ctx.send(f"```json\n{json_str}\n```")
            if found_count >= amount: break

if __name__ == "__main__":
    # Chạy Web Server trước khi chạy Bot
    keep_alive()
    bot.run(TOKEN)