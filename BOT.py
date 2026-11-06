import os
import asyncio
import datetime

import discord
from discord.ext import commands, tasks
from Myserver import server_on


# ====== ตั้งค่า ======
CHANNEL_ID = 1564607249903657150          # ไอดีของช่องที่ต้องการให้บอททำงาน
EXPIRE_AFTER = datetime.timedelta(hours=3)   # เวลาที่ต้องรอก่อนเปลี่ยน ✅ เป็น ❌
LOOKBACK = datetime.timedelta(hours=48)      # ให้บอทตรวจย้อนหลังกี่ชั่วโมง (กันกรณีบอทปิดไปนาน)
CHECK_INTERVAL_SECONDS = 60                  # ตรวจทุกกี่วินาที

CHECK_EMOJI = "✅"
CROSS_EMOJI = "❌"
# =====================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"ล็อกอินเป็น {bot.user} แล้ว")
    if not check_expired.is_running():
        check_expired.start()


@bot.event
async def on_message(message: discord.Message):
    # ทำงานเฉพาะช่องที่กำหนด และไม่ติ๊กข้อความของบอทเอง
    if message.channel.id != CHANNEL_ID:
        return
    if bot.user is None or message.author.id == bot.user.id:
        return
    try:
        await message.add_reaction(CHECK_EMOJI)
    except discord.HTTPException as e:
        print(f"เพิ่มรีแอคชันไม่สำเร็จ: {e}")

    await bot.process_commands(message)


@tasks.loop(seconds=CHECK_INTERVAL_SECONDS)
async def check_expired():
    """ตรวจข้อความที่มี ✅ จากบอทและอายุเกิน 6 ชั่วโมง แล้วเปลี่ยนเป็น ❌
    (ไม่เก็บสถานะไว้ในหน่วยความจำ จึงยังทำงานต่อได้แม้รีสตาร์ทบอท)"""
    channel = bot.get_channel(CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel) or bot.user is None:
        return

    now = discord.utils.utcnow()
    cutoff = now - EXPIRE_AFTER

    async for msg in channel.history(limit=None, after=now - LOOKBACK):
        if msg.created_at > cutoff:
            continue  # ยังไม่ครบ 6 ชั่วโมง

        has_check = any(
            str(r.emoji) == CHECK_EMOJI and r.me for r in msg.reactions
        )
        if not has_check:
            continue

        try:
            await msg.remove_reaction(CHECK_EMOJI, bot.user)
            await msg.add_reaction(CROSS_EMOJI)
        except discord.HTTPException as e:
            print(f"เปลี่ยนรีแอคชันไม่สำเร็จ ({msg.id}): {e}")
        await asyncio.sleep(0.5)  # กัน rate limit


@check_expired.before_loop
async def before_check():
    await bot.wait_until_ready()

server_on()  # เรียกใช้งานเซิร์ฟเวอร์ Flask
bot.run(os.getenv('DISCORD_TOKEN'))  # ใช้ TOKEN จาก environment variable ถ้ามี
