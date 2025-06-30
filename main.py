import discord
import os
from discord import app_commands
from dotenv import load_dotenv
from flask import Flask
import threading
import aiohttp   # <-- এখানে ইমপোর্ট করুন
from utils import check_ban


app = Flask(__name__)

@app.route('/')
def home():
    return f"Bot is working"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_flask).start()

load_dotenv()
TOKEN = os.getenv("TOKEN")

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

client = MyClient()
registered_channels = {}
user_languages = {}
DEFAULT_LANG = "en"

@client.event
async def on_ready():
    await client.tree.sync()
    print(f"✅ Logged in as {client.user}")

# -------- /setup --------
@client.tree.command(name="setup", description="Register this channel for bot commands")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    registered_channels[interaction.guild.id] = interaction.channel.id
    await interaction.response.send_message("✅ This channel is now registered for bot commands.", ephemeral=True)

async def is_registered(interaction: discord.Interaction):
    return registered_channels.get(interaction.guild.id) == interaction.channel.id

# -------- /lang --------
@client.tree.command(name="lang", description="Change language")
@app_commands.describe(lang_code="Language code: en or fr")
async def lang(interaction: discord.Interaction, lang_code: str):
    lang_code = lang_code.lower()
    if lang_code not in ["en", "fr"]:
        await interaction.response.send_message("❌ Invalid language. Use 'en' or 'fr'", ephemeral=True)
        return
    user_languages[interaction.user.id] = lang_code
    msg = "✅ Language set to English." if lang_code == 'en' else "✅ Langue définie sur le français."
    await interaction.response.send_message(msg, ephemeral=True)

# -------- /guilds --------
@client.tree.command(name="guilds", description="Show all servers this bot is in")
async def guilds(interaction: discord.Interaction):
    if not client.guilds:
        await interaction.response.send_message("❌ Bot is not in any servers.", ephemeral=True)
        return
    guild_list = "\n".join([f"{i+1}. {g.name}" for i, g in enumerate(client.guilds)])
    await interaction.response.send_message(f"📋 Bot is in the following servers:\n{guild_list}")

# -------- /like --------
@client.tree.command(name="like", description="Send like to Free Fire UID")
@app_commands.describe(uid="Enter Free Fire UID")
async def like(interaction: discord.Interaction, uid: str):
    if not await is_registered(interaction):
        await interaction.response.send_message("❌ This channel is not registered. Use /setup", ephemeral=True)
        return
    if not uid.isdigit():
        await interaction.response.send_message("❌ Invalid UID! Example: /like 123456789", ephemeral=True)
        return
    url = f"https://like-dita.onrender.com/like?uid={uid}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                data = await resp.json()

            if data.get("status") == 400:
                await interaction.response.send_message(
                    f"❌ Error: {data.get('error')}\n📌 Message: {data.get('message')}"
                )
                return

            if data.get("status") == 1:
                info = (
                    f"┌ FREE FIRE LIKE ADDED\n"
                    f"├─ Nickname: {data.get('nickname')}\n"
                    f"├─ Region: {data.get('region')}\n"
                    f"├─ Likes Before: {data.get('likes_before')}\n"
                    f"├─ Likes Added: {data.get('likes_added')}\n"
                    f"└─ Likes After: {data.get('likes_after')}\n"
                    f"UID: `{data.get('uid')}`"
                )
                embed = discord.Embed(
                    title="🔥 Free Fire Like Added!",
                    description=f"```{info}```",
                    color=discord.Color.purple()
                )
                embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
                embed.set_image(url="https://i.imgur.com/ajygBes.gif")
                embed.set_footer(text="📌 Dev </> GAMER SABBIR")
                await interaction.response.send_message(embed=embed)
                return

            await interaction.response.send_message("⚠️ Unexpected error. Please try again later.")

        except Exception as e:
            await interaction.response.send_message(f"❌ Error:\n```{str(e)}```")

# -------- /id --------
@client.tree.command(name="id", description="Check Free Fire ID ban status")
@app_commands.describe(uid="Enter Free Fire UID")
async def check_ban_cmd(interaction: discord.Interaction, uid: str):
    if not await is_registered(interaction):
        await interaction.response.send_message("❌ This channel is not registered. Use /setup", ephemeral=True)
        return

    await interaction.response.defer()  # Prevent timeout

    lang = user_languages.get(interaction.user.id, "en")

    if not uid.isdigit():
        msg = {
            "en": "❌ Invalid UID! Example: /id 123456789",
            "fr": "❌ UID invalide ! Exemple : /id 123456789"
        }
        await interaction.followup.send(msg[lang], ephemeral=True)
        return

    try:
        ban_status = await check_ban(uid)
        if ban_status is None:
            await interaction.followup.send("❌ Could not get info. Try again later.", ephemeral=True)
            return

        is_banned = int(ban_status.get("is_banned", 0))
        period = ban_status.get("period", "N/A")
        nickname = ban_status.get("nickname", "NA")
        region = ban_status.get("region", "N/A")
        period_str = f"more than {period} months" if isinstance(period, int) else "unavailable"

        if is_banned:
            title = "**▌ Banned Account 🛑**"
            desc = (
                "┌ BAN STATUS\n"
                f"├─ Reason: This account was confirmed for using cheats.\n"
                f"├─ Suspension duration: {period_str}\n"
                f"├─ Nickname: {nickname}\n"
                f"├─ Player ID: `{uid}`\n"
                f"└─ Region: {region}"
            )
            color = 0xFF0000
            image = "https://i.imgur.com/6PDA32M.gif"
        else:
            title = "**▌ Clean Account ✅**"
            desc = (
                "┌ BAN STATUS\n"
                f"├─ Status: No evidence of cheat usage.\n"
                f"├─ Nickname: {nickname}\n"
                f"├─ Player ID: `{uid}`\n"
                f"└─ Region: {region}"
            )
            color = 0x00FF00
            image = "https://i.imgur.com/166jkZ7.gif"

        embed = discord.Embed(
            title=title,
            description=f"```{desc}```",
            color=color
        )
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.set_image(url=image)
        embed.set_footer(text="📌 Dev </> GAMER SABBIR")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Error:\n```{str(e)}```", ephemeral=True)


# -------- /help --------
@client.tree.command(name="help", description="Show all available bot commands")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "📘 **Available Commands:**\n\n"
        "**/setup** — Register this channel for bot commands\n"
        "**/lang [en|fr]** — Set your preferred language\n"
        "**/guilds** — Show all servers the bot is in\n"
        "**/like [uid]** — Add like to Free Fire UID\n"
        "**/id [uid]** — Check ban status of a Free Fire ID\n"
        "**/info [uid]** — Get detailed player info by UID\n"
        "**/help** — Show this help message"
    )

    embed = discord.Embed(
        title="📖 Help Menu",
        description=help_text,
        color=discord.Color.green()
    )
    embed.set_footer(text="📌 Dev </> GAMER SABBIR")
    await interaction.response.send_message(embed=embed, ephemeral=True)



# -------- /info --------
@client.tree.command(name="info", description="Get detailed player info by UID")
@app_commands.describe(uid="Enter Free Fire UID")
async def playerinfo(interaction: discord.Interaction, uid: str):
    if not await is_registered(interaction):
        await interaction.response.send_message("❌ This channel is not registered. Use /setup", ephemeral=True)
        return

    if not uid.isdigit():
        await interaction.response.send_message("❌ Invalid UID! Example: /info 123456789", ephemeral=True)
        return

    url = f"https://api-info-gb.up.railway.app/info?uid={uid}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                data = await response.json()

                if "detail" in data:
                    await interaction.response.send_message(f"❌ {data['detail']}", ephemeral=True)
                    return

                info = data["basicInfo"]
                pet = data.get("petInfo", {})
                clan = data.get("clanBasicInfo", {})
                captain = data.get("captainBasicInfo", {})
                social = data.get("socialInfo", {})

                def convert_time(timestamp):
                    from datetime import datetime
                    return datetime.utcfromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M:%S")

                # Create the embed
                embed = discord.Embed(
                    title=f"📘 Player Profile — {info['nickname']}",
                    description=f"{interaction.user.mention}, here is the player information:",
                    color=discord.Color.dark_blue()
                )

                embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
                embed.set_image(url=f"https://profile-aimguard.vercel.app/generate-profile?uid={uid}&region={info['region'].lower()}")

                # 👤 Player Info
                embed.add_field(
                    name="👤 Player Info",
                    value=(
                        f"   ```┌ Name: {info['nickname']}\n"
                        f"  ├─ UID: {info['accountId']}\n"
                        f"  ├─ Level: {info['level']} (Exp: {info['exp']})\n"
                        f"  ├─ Region: {info['region']}\n"
                        f"  ├─ Likes: {info['liked']}\n"
                        f"  ├─ Honor Score: {data['creditScoreInfo']['creditScore']}\n"
                        f"  └─ Signature: {social.get('signature', 'N/A')}```"
                    ),
                    inline=False
                )

                # 🎮 Activity
                embed.add_field(
                    name="🎮 Player Activity",
                    value=(
                        f"   ```┌ OB Version: {info['releaseVersion']}\n"
                        f"  ├─ BR Rank: {info['rankingPoints']}\n"
                        f"  ├─ CS Points: 0\n"
                        f"  ├─ Account Created: {convert_time(info['createAt'])}\n"
                        f"  └─ Last Login: {convert_time(info['lastLoginAt'])}```"
                    ),
                    inline=False
                )

                # 🐾 Pet Info
                embed.add_field(
                    name="🐾 Pet Info",
                    value=(
                        f"  ```┌ Name: {pet.get('name', 'N/A')}\n"
                        f"  ├─ Level: {pet.get('level', 'N/A')}\n"
                        f"  └─ Exp: {pet.get('exp', 'N/A')}```"
                    ),
                    inline=False
                )

                # 🏰 Guild Info
                embed.add_field(
                    name="🏰 Guild Info",
                    value=(
                        f"   ```┌ Name: {clan.get('clanName', 'N/A')}\n"
                        f"  ├─ ID: {clan.get('clanId', 'N/A')}\n"
                        f"  ├─ Level: {clan.get('clanLevel', 'N/A')}\n"
                        f"  └─ Members: {clan.get('memberNum', 'N/A')}```"
                    ),
                    inline=False
                )

                # 👑 Guild Leader
                embed.add_field(
                    name="👑 Guild Leader",
                    value=(
                        f"   ```┌ Name: {captain.get('nickname', 'N/A')}\n"
                        f"  ├─ Level: {captain.get('level', 'N/A')}\n"
                        f"  ├─ UID: {captain.get('accountId', 'N/A')}\n"
                        f"  ├─ Likes: {captain.get('liked', 'N/A')}\n"
                        f"  ├─ BR Points: {captain.get('rankingPoints', 'N/A')}\n"
                        f"  └─ Last Login: {convert_time(captain.get('lastLoginAt', '0'))}```"
                    ),
                    inline=False
                )

                embed.set_footer(text="📌 Dev </> GAMER SABBIR")
                await interaction.response.send_message(embed=embed)

        except Exception as e:
            try:
                await interaction.response.send_message(f"❌ Error occurred:\n```{str(e)}```", ephemeral=True)
            except discord.errors.HTTPException:
                await interaction.followup.send(f"❌ Error occurred:\n```{str(e)}```", ephemeral=True)






client.run(TOKEN)
