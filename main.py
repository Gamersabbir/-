import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
import threading
import aiohttp
from utils import check_ban
import requests

app = Flask(__name__)

load_dotenv()
APPLICATION_ID = os.getenv("APPLICATION_ID")
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DEFAULT_LANG = "en"
user_languages = {}

nomBot = "None"

# সার্ভার আইডি অনুযায়ী রেজিস্টার্ড চ্যানেল আইডি রাখার ডিকশনারি
registered_channels = {}

@app.route('/')
def home():
    global nomBot
    return f"Bot {nomBot} is working"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_flask).start()

@bot.event
async def on_ready():
    global nomBot
    nomBot = f"{bot.user}"
    print(f"Le bot est connecté en tant que {bot.user}")




# ---------- নতুন !setup কমান্ড ----------
@bot.command(name="setup", aliases=["SETUP", "Setup"])
@commands.has_permissions(administrator=True)  # শুধুমাত্র অ্যাডমিনরা চালাতে পারবে
async def setup(ctx):
    server_id = ctx.guild.id
    channel_id = ctx.channel.id
    registered_channels[server_id] = channel_id
    await ctx.send(f"এই সার্ভারের জন্য এই চ্যানেল (ID: <#{channel_id}>) রেজিস্টার করা হলো। এখন থেকে এই চ্যানেলেই কমান্ড চলবে।")

# ---------- চ্যানেল চেক করার চেক ----------
def is_registered_channel():
    def predicate(ctx):
        server_id = ctx.guild.id
        if server_id not in registered_channels:
            return False  # setup হয় নাই, কাজ করবে না
        # চ্যানেল ম্যাচ করানো হচ্ছে
        return ctx.channel.id == registered_channels[server_id]
    return commands.check(predicate)

@bot.command(name="guilds", aliases=["GUILDS", "Guilds"])
async def show_guilds(ctx):
    guild_names = [f"{i+1}. {guild.name}" for i, guild in enumerate(bot.guilds)]
    guild_list = "\n".join(guild_names)
    await ctx.send(f"Le bot est dans les guilds suivantes :\n{guild_list}")

@bot.command(name="lang", aliases=["LANG", "Lang"])
async def change_language(ctx, lang_code: str):
    lang_code = lang_code.lower()
    if lang_code not in ["en", "fr"]:
        await ctx.send("❌ Invalid language. Available: `en`, `fr`")
        return

    user_languages[ctx.author.id] = lang_code
    message = "✅ Language set to English  And  Bangla  ." if lang_code == 'en' else "✅ Langue définie sur le français."
    await ctx.send(f"{ctx.author.mention} {message}")




@bot.command(name="ID")
@is_registered_channel()  # শুধু রেজিস্টার্ড চ্যানেলে কাজ করবে
async def check_ban_command(ctx):
    content = ctx.message.content
    user_id = content[3:].strip()
    lang = user_languages.get(ctx.author.id, "en")

    print(f"Commande fait par {ctx.author} (lang={lang})")

    if not user_id.isdigit():
        message = {
            "en": f"{ctx.author.mention} ❌ **Invalid UID!**\n➡️ Please use: `!ID 123456789`",
            "fr": f"{ctx.author.mention} ❌ **UID invalide !**\n➡️ Veuillez fournir un UID valide sous la forme : `!ID 123456789`"
        }
        await ctx.send(message[lang])
        return

    async with ctx.typing():
        try:
            ban_status = await check_ban(user_id)
        except Exception as e:
            await ctx.send(f"{ctx.author.mention} ⚠️ Error:\n```{str(e)}```")
            return

        if ban_status is None:
            message = {
                "en": f"{ctx.author.mention} ❌ **Could not get information. Please try again later.**",
                "fr": f"{ctx.author.mention} ❌ **Impossible d'obtenir les informations.**\nVeuillez réessayer plus tard."
            }
            await ctx.send(message[lang])
            return

        is_banned = int(ban_status.get("is_banned", 0))
        period = ban_status.get("period", "N/A")
        nickname = ban_status.get("nickname", "NA")
        region = ban_status.get("region", "N/A")
        id_str = f"`{user_id}`"

        if isinstance(period, int):
            period_str = f"more than {period} months" if lang == "en" else f"plus de {period} mois"
        else:
            period_str = "unavailable" if lang == "en" else "indisponible"

        embed = discord.Embed(
            color=0xFF0000 if is_banned else 0x00FF00,
            timestamp=ctx.message.created_at
        )

        if is_banned:
            embed.title = "**▌ Banned Account 🛑 **" if lang == "en" else "**▌ Compte banni 🛑 **"
            embed.description = (
                f"**• {'Reason' if lang == 'en' else 'Raison'} :** "
                f"{'This account was confirmed for using cheats.' if lang == 'en' else 'Ce compte a été confirmé comme utilisant des hacks.'}\n"
                f"**• {'Suspension duration' if lang == 'en' else 'Durée de la suspension'} :** {period_str}\n"
                f"**• {'Nickname' if lang == 'en' else 'Pseudo'} :** `{nickname}`\n"
                f"**• {'Player ID' if lang == 'en' else 'ID du joueur'} :** `{id_str}`\n"
                f"**• {'Region' if lang == 'en' else 'Région'} :** `{region}`"
            )
            embed.set_image(url="https://i.imgur.com/6PDA32M.gif")
        else:
            embed.title = "**▌ Clean Account ✅ **" if lang == "en" else "**▌ Compte non banni ✅ **"
            embed.description = (
                f"**• {'Status' if lang == 'en' else 'Statut'} :** "
                f"{'No sufficient evidence of cheat usage on this account.' if lang == 'en' else 'Aucune preuve suffisante pour confirmer l’utilisation de hacks sur ce compte.'}\n"
                f"**• {'Nickname' if lang == 'en' else 'Pseudo'} :** `{nickname}`\n"
                f"**• {'Player ID' if lang == 'en' else 'ID du joueur'} :** `{id_str}`\n"
                f"**• {'Region' if lang == 'en' else 'Région'} :** `{region}`"
            )
            embed.set_image(url="https://i.imgur.com/166jkZ7.gif")

        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.set_footer(text="📌  Dev</>!      GAMER SABBIR")
        await ctx.send(f"{ctx.author.mention}", embed=embed)






# ---------- নতুন playerinfo কমান্ড ----------


@bot.command(name="INFO")
@is_registered_channel()
async def player_info(ctx, uid: str):
    if not uid.isdigit():
        await ctx.send(f"{ctx.author.mention} ❌ Invalid UID!")
        return

    url = f"https://player-track.vercel.app/info?uid={uid}"

    async with ctx.typing():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise Exception(f"API returned status {resp.status}")
                    data = await resp.json()

            player_data = data.get("data", {})
            info = player_data.get("player_info", {})
            if not info:
                raise Exception("No player_info found in API response.")
            guild = player_data.get("guildInfo", {})
            leader = guild.get("owner_basic_info", {})
            pet = player_data.get("petInfo", {})

            embed = discord.Embed(
                title=f"📘 Player Info: {info.get('nickname', 'N/A')}",
                color=discord.Color.dark_blue()
            )

            # Account Basic Info
            embed.add_field(name="👤 ACCOUNT BASIC INFO", value=f"""```yaml
Name: {info.get('nickname', 'N/A')}
UID: {info.get('uid', 'N/A')}
Level: {info.get('level', 'N/A')} (Exp: {info.get('exp', 'N/A')})
Region: {info.get('region', 'N/A')}
Likes: {info.get('likes', 'N/A')}
Honor Score: {info.get('honor_score', 'N/A')}
Signature: {info.get('signature', 'N/A')}
```""", inline=False)

            # Account Activity
            embed.add_field(name="🎮 ACCOUNT ACTIVITY", value=f"""```yaml
Most Recent OB: {info.get('release_version', 'N/A')}
BP Badges: {info.get('badge_num', 'N/A')}
BR Rank: {info.get('br_rank_points', 'N/A')}
CS Points: {info.get('cs_rank_points', 'N/A')}
Created At: {info.get('account_created', 'N/A')}
Last Login: {info.get('last_login', 'N/A')}
```""", inline=False)

            # Overview
            embed.add_field(name="👕 ACCOUNT OVERVIEW", value=f"""```yaml
Avatar ID: {info.get('avatar_id', 'N/A')}
Banner ID: {info.get('banner_id', 'N/A')}
Title ID: {info.get('title_id', 'N/A')}
```""", inline=False)

            # Pet Info
            embed.add_field(name="🐾 PET DETAILS", value=f"""```yaml
Equipped?: {'Yes' if pet else 'No'}
Pet Name: {pet.get('name', 'N/A')}
Pet Exp: {pet.get('exp', 'N/A')}
Pet Level: {pet.get('level', 'N/A')}
```""", inline=False)

            # Guild Info
            embed.add_field(name="🛡️ GUILD INFO", value=f"""```yaml
Guild Name: {guild.get('name', 'N/A')}
Guild ID: {guild.get('id', 'N/A')}
Guild Level: {guild.get('level', 'N/A')}
Live Members: {guild.get('members', 'N/A')}
```""", inline=False)

            # Leader Info
            embed.add_field(name="🏅 LEADER INFO", value=f"""```yaml
Leader Name: {leader.get('nickname', 'N/A')}
Leader UID: {leader.get('uid', 'N/A')}
Leader Level: {leader.get('level', 'N/A')} (Exp: {leader.get('exp', 'N/A')})
Created At: {leader.get('account_created', 'N/A')}
Last Login: {leader.get('last_login', 'N/A')}
BR Points: {leader.get('br_rank_points', 'N/A')}
CS Points: {leader.get('cs_rank_points', 'N/A')}
```""", inline=False)

            embed.set_image(url="https://i.imgur.com/ajygBes.gif")
            embed.set_footer(text="📌 Dev</>!      GAMER SABBIR")

            await ctx.send(f"{ctx.author.mention}", embed=embed)

        except Exception as e:
            await ctx.send(f"{ctx.author.mention} ❌ Error fetching player info:\n```{str(e)}```")

bot.run(TOKEN)
