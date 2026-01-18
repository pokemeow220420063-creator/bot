import os
import discord
from discord.ext import commands
import json
from threading import Thread
from flask import Flask
from dotenv import load_dotenv

# Tải biến môi trường
load_dotenv()

# --- CẤU HÌNH WEB SERVER (GIỮ BOT CHẠY 24/7) ---
app = Flask('')

@app.route('/')
def home():
    return "✅ Scanner Bot is Online and Running 24/7!"

def run_web():
    # Lấy cổng từ hệ thống (mặc định 8080 cho Render/Railway)
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- CẤU HÌNH BOT QUÉT ---
TOKEN = os.getenv("TOKEN")
POKEMEOW_ID = 664508672713424926

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=";", intents=intents)

def parse_to_dict(msg):
    """Phân tích tin nhắn thành JSON đầy đủ nhất"""
    data = {
        "id": msg.id,
        "author": str(msg.author),
        "content": msg.content,
        "embeds": [],
        "components": []
    }
    
    # Xử lý Embeds (Spawn, Inventory, Info...)
    for emb in msg.embeds:
        e_data = {
            "author": emb.author.name if emb.author else None,
            "title": emb.title,
            "description": emb.description,
            "footer": emb.footer.text if emb.footer else None,
            "fields": []
        }
        # Quan trọng: Lấy toàn bộ Fields (Nơi chứa Inventory)
        if emb.fields:
            for field in emb.fields:
                e_data["fields"].append({
                    "name": field.name,
                    "value": field.value
                })
        data["embeds"].append(e_data)
    
    # Xử lý Nút bấm (Buttons)
    for row in msg.components:
        for comp in row.children:
            if isinstance(comp, discord.Button):
                data["components"].append({
                    "label": comp.label,
                    "custom_id": comp.custom_id,
                    "emoji": str(comp.emoji) if comp.emoji else None
                })
    return data

@bot.event
async def on_ready():
    print(f"--- SCANNER BOT READY: {bot.user} ---")

@bot.command(name="l")
async def latest_data(ctx, amount: int = 1):
    """Lệnh ;l để lấy dữ liệu PokéMeow gần nhất"""
    found = 0
    async for message in ctx.channel.history(limit=50):
        if message.author.id == POKEMEOW_ID:
            found += 1
            raw_data = parse_to_dict(message)
            json_str = json.dumps(raw_data, ensure_ascii=False, indent=2)
            
            # Nếu JSON quá dài, gửi dạng File
            if len(json_str) > 1900:
                with open("latest_data.json", "w", encoding="utf-8") as f:
                    f.write(json_str)
                await ctx.send(f"📄 Dữ liệu {message.id} (File):", file=discord.File("latest_data.json"))
            else:
                await ctx.send(f"```json\n{json_str}\n```")
            
            if found >= amount:
                break
    if found == 0:
        await ctx.send("❌ Không tìm thấy tin nhắn nào từ PokéMeow.")

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
