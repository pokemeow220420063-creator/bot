import os
import discord
from discord.ext import commands
import json
from threading import Thread
from flask import Flask
from dotenv import load_dotenv
from datetime import datetime # Thêm thư viện thời gian

# Tải biến môi trường
load_dotenv()

# --- CẤU HÌNH WEB SERVER (GIỮ BOT CHẠY 24/7) ---
app = Flask('')

@app.route('/')
def home():
    return "✅ Scanner Bot is Online and Running 24/7!"

def run_web():
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

def parse_message_full(msg):
    """
    Hàm phân tích tin nhắn siêu chi tiết.
    Lấy tất cả mọi thứ có thể từ object Message.
    """
    # 1. Thông tin cơ bản
    data = {
        "id": msg.id,
        "channel_id": msg.channel.id,
        "guild_id": msg.guild.id if msg.guild else None,
        "created_at": str(msg.created_at),
        "edited_at": str(msg.edited_at) if msg.edited_at else None,  # ⭐ QUAN TRỌNG
        "is_edited": msg.edited_at is not None,                      # ⭐ RẤT TIỆN
        "content": msg.content,
        "jump_url": msg.jump_url,
        "flags": dict(msg.flags)
    }


    # 2. Thông tin người gửi (Author)
    data["author"] = {
        "id": msg.author.id,
        "name": msg.author.name,
        "discriminator": msg.author.discriminator,
        "bot": msg.author.bot,
        "avatar_url": str(msg.author.avatar.url) if msg.author.avatar else None,
        "display_name": msg.author.display_name
    }

    # 3. Xử lý Attachments (File đính kèm/Ảnh gửi thường)
    data["attachments"] = []
    for att in msg.attachments:
        data["attachments"].append({
            "id": att.id,
            "filename": att.filename,
            "url": att.url,
            "content_type": att.content_type,
            "size": att.size
        })

    # 4. Xử lý Embeds (Cực kỳ quan trọng với PokéMeow)
    data["embeds"] = []
    for emb in msg.embeds:
        e_data = {
            "title": emb.title,
            "description": emb.description,
            "url": emb.url,
            "color": emb.color.value if emb.color else None,
            "timestamp": str(emb.timestamp) if emb.timestamp else None,
            "footer": {"text": emb.footer.text, "icon_url": emb.footer.icon_url} if emb.footer else None,
            "image": {"url": emb.image.url} if emb.image else None, # Ảnh to (thường là Captcha/Pokemon)
            "thumbnail": {"url": emb.thumbnail.url} if emb.thumbnail else None, # Ảnh nhỏ góc phải
            "author": {
                "name": emb.author.name,
                "url": emb.author.url,
                "icon_url": emb.author.icon_url
            } if emb.author else None,
            "fields": []
        }
        
        # Lấy Fields
        for field in emb.fields:
            e_data["fields"].append({
                "name": field.name,
                "value": field.value,
                "inline": field.inline
            })
        data["embeds"].append(e_data)

    # 5. Xử lý Components (Nút bấm, Menu thả xuống)
    data["components"] = []
    # Discord chia components thành các ActionRow
    for row in msg.components:
        row_data = {"type": "ActionRow", "children": []}
        for comp in row.children:
            comp_data = {
                "custom_id": getattr(comp, "custom_id", None),
                "disabled": getattr(comp, "disabled", False),
                "type": str(comp.type)
            }
            
            # Nếu là Nút (Button)
            if isinstance(comp, discord.Button):
                comp_data["label"] = comp.label
                comp_data["style"] = str(comp.style)
                comp_data["url"] = comp.url
                comp_data["emoji"] = {
                    "name": comp.emoji.name,
                    "id": comp.emoji.id,
                    "animated": comp.emoji.animated
                } if comp.emoji else None

            # Nếu là Select Menu (Dropdown)
            elif isinstance(comp, discord.SelectMenu):
                comp_data["placeholder"] = comp.placeholder
                comp_data["min_values"] = comp.min_values
                comp_data["max_values"] = comp.max_values
                comp_data["options"] = [
                    {"label": opt.label, "value": opt.value, "description": opt.description, "emoji": str(opt.emoji) if opt.emoji else None}
                    for opt in comp.options
                ]
            
            row_data["children"].append(comp_data)
        data["components"].append(row_data)

    # 6. Tin nhắn Reply (Referenced Message)
    if msg.reference and msg.reference.message_id:
        data["referenced_message_id"] = msg.reference.message_id

    return data

@bot.event
async def on_ready():
    print(f"--- SCANNER BOT READY: {bot.user} ---")

@bot.command(name="l")
async def latest_data(ctx, amount: int = 1):
    """
    Lệnh ;l [số lượng]
    Dump tin nhắn thành file JSON có tên theo thời gian thực.
    """
    found_messages = []
    count = 0
    
    status_msg = await ctx.send(f"🔍 Đang quét {amount} tin nhắn gần nhất của PokéMeow...")

    async for message in ctx.channel.history(limit=50): # Quét 50 tin gần nhất để lọc
        if message.author.id == POKEMEOW_ID:
            # Phân tích tin nhắn
            parsed_data = parse_message_full(message)
            found_messages.append(parsed_data)
            count += 1
            
            if count >= amount:
                break
    
    if not found_messages:
        await status_msg.edit(content="❌ Không tìm thấy tin nhắn nào từ PokéMeow trong phạm vi quét.")
        return

    # --- TẠO FILE VÀ GỬI ---
    try:
        # 1. Tạo tên file theo thời gian hiện tại: dump_NămThángNgày_GiờPhútGiây.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"dump_{timestamp}.json"
        
        # 2. Ghi dữ liệu vào file
        with open(file_name, "w", encoding="utf-8") as f:
            # Đảo ngược list để tin nhắn cũ nhất lên đầu, mới nhất dưới cùng (dễ đọc)
            json.dump(found_messages[::-1], f, ensure_ascii=False, indent=4)
        
        # 3. Gửi file lên Discord
        await ctx.send(
            content=f"✅ **Đã trích xuất {len(found_messages)} tin nhắn.**\n📄 File: `{file_name}`", 
            file=discord.File(file_name)
        )
        
        # 4. Xóa file sau khi gửi để dọn rác server
        os.remove(file_name)
        await status_msg.delete()
        
    except Exception as e:
        await ctx.send(f"⚠️ Có lỗi khi tạo file: {e}")

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
