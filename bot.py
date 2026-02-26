import discord
from discord.ext import commands
import sqlite3
import os
from io import BytesIO
import datetime
from dotenv import load_dotenv
from typing import Optional

load_dotenv()
TOKEN = os.getenv("TOKEN")
BADGE_PREFIX = "NR"

# ---------------------------
# BOT SETUP
# ---------------------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=";", intents=intents)
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
# ---------------------------
# DATABASE SETUP
# ---------------------------
conn = sqlite3.connect("nari.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    badge_id TEXT,
    registered_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS counter (
    id INTEGER PRIMARY KEY,
    value INTEGER
)
""")

cursor.execute("INSERT OR IGNORE INTO counter (id, value) VALUES (1, 1)")
conn.commit()

# ---------------------------
# VISA DONE
# ---------------------------
@bot.command()
@commands.has_any_role("Visa Officer", "Admin")
async def visa(ctx, status: str, member: discord.Member):
    if status.lower() != "done":
        await ctx.send("❌ Use: ;visa done @user")
        return

    # Check if user already has badge
    cursor.execute("SELECT badge_id FROM users WHERE user_id = ?", (member.id,))
    existing = cursor.fetchone()
    if existing:
        await ctx.send(f"⚠️ User already has badge: {existing[0]}")
        return

    # Get counter
    cursor.execute("SELECT value FROM counter WHERE id = 1")
    counter = cursor.fetchone()[0]
    badge_id = f"{BADGE_PREFIX}-{counter:05d}"

    # Save badge
    cursor.execute("INSERT INTO users (user_id, badge_id, registered_at) VALUES (?, ?, ?)", 
                   (member.id, badge_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    cursor.execute("UPDATE counter SET value = value + 1 WHERE id = 1")
    conn.commit()

    role = discord.utils.get(ctx.guild.roles, name="Verified")
    if role:
        await member.add_roles(role)

    await ctx.send(f"✅ VISA Approved for {member.mention}\n🎖 Badge ID: **{badge_id}**")

# ---------------------------
# CHECK BADGE
# ---------------------------
@bot.command()
async def badge(ctx, member: Optional[discord.Member] = None):
    member = member or ctx.author
    cursor.execute("SELECT badge_id FROM users WHERE user_id = ?", (member.id,))
    result = cursor.fetchone()
    if result:
        await ctx.send(f"🎖 {member.mention} Badge ID: **{result[0]}**")
    else:
        await ctx.send("❌ No badge found.")

# ---------------------------
# DELETE BADGE
# ---------------------------
@bot.command()
@commands.has_any_role("Visa Officer", "Admin")
async def deletebadge(ctx, member: discord.Member):
    cursor.execute("SELECT badge_id FROM users WHERE user_id = ?", (member.id,))
    result = cursor.fetchone()
    if not result:
        await ctx.send("❌ This user does not have a badge.")
        return

    cursor.execute("DELETE FROM users WHERE user_id = ?", (member.id,))
    conn.commit()

    role = discord.utils.get(ctx.guild.roles, name="Verified")
    if role:
        await member.remove_roles(role)

    await ctx.send(f"🗑️ Badge deleted for {member.mention}")

# ---------------------------
# PASSPORT ASCII (instead of PNG)
# ---------------------------
@bot.command()
async def passport(ctx, member: Optional[discord.Member] = None):
    member = member or ctx.author
    cursor.execute("SELECT badge_id, registered_at FROM users WHERE user_id = ?", (member.id,))
    data = cursor.fetchone()

    if not data:
        await ctx.send("❌ This user does not have a passport.")
        return

    badge_id, registered_at = data

    ascii_passport = (
        "```"
        "\n┌─────────────────────────────────┐"
        "\n│      NARI GAMING REPUBLIC       │"
        "\n│    OFFICIAL DIGITAL PASSPORT    │"
        "\n├─────────────────────────────────┤"
        f"\n│ NAME: {member.name[:20]:<23}│"
        f"\n│ BADGE ID: {badge_id:<21}│"
        f"\n│ REGISTERED: {registered_at:<17}│"
        f"\n│ CITIZEN ID: {member.id:<19}│"
        "\n├─────────────────────────────────┤"
        "\n│ STATUS: VERIFIED MEMBER         │"
        "\n└─────────────────────────────────┘"
        "\n```"
    )

    await ctx.send(ascii_passport)

# ---------------------------
# KICK
# ---------------------------
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member} kicked. Reason: {reason}")

# ---------------------------
# ADD ROLE / REMOVE ROLE
# ---------------------------
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"➕ Added {role.name} to {member.mention}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f"➖ Removed {role.name} from {member.mention}")

# ---------------------------
# ACCEPT / REJECT
# ---------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def accept(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Member")
    if role:
        await member.add_roles(role)
    await ctx.send(f"✅ Application accepted for {member.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def reject(ctx, member: discord.Member):
    await ctx.send(f"❌ Application rejected for {member.mention}")

# ---------------------------
# ERROR HANDLING
# ---------------------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("🚫 You don't have permission to use this command.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You lack the required Discord permissions.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❓ Unknown command.")
    else:
        await ctx.send(f"⚠️ Error: {str(error)}")
# ---------------------------
# COMMAND LIST
# ---------------------------
@bot.command()
async def cmdlist(ctx):
    command_list = [command.name for command in bot.commands]
    await ctx.send("📜 **Available Commands:**\n" + "\n".join(command_list))

if TOKEN is None:
    print("❌ ERROR: TOKEN not found in .env file")
else:
    print("✅ TOKEN LOADED")
    bot.run(TOKEN)