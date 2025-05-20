import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
import threading
from utils import check_ban

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


@bot.command(name="help", aliases=["HELP", "Help")
async def help_command(ctx):
    embed = discord.Embed(
        title="🤖 BOT ব্যবহারের নির্দেশনা",
        description=(
            "**🔧 প্রথমে `!setup` কমান্ড দিয়ে চ্যানেল সেট করুন।**\n"
            "এই কমান্ডটি যে চ্যানেলে দেওয়া হবে, কেবল সেই চ্যানেলেই বট কাজ করবে।\n\n"
            "**📌 উদাহরণ:**\n"
            "`!setup`\n\n"
            "**🛑 অন্য কোনো চ্যানেলে কমান্ড দিলে বট কাজ করবে না।**\n\n"
            "**✅ `!setup` করার পর আপনি এই কমান্ডগুলো ব্যবহার করতে পারবেন:**\n"
            "• `!ID 123456789` → ইউজারের ব্যান চেক করুন\n"
            "• `!lang en` বা `!lang fr` → ভাষা পরিবর্তন\n"
            "• `!guilds` → বট কোন কোন সার্ভারে আছে দেখুন\n\n"
            "**❗  `!setup` না করলে বট কাজ করবে না।**"
        ),
        color=0x3498db
    )
    embed.set_footer(text="📌 Bot by GAMER SABBIR")
    await ctx.send(embed=embed)

# ---------- নতুন !setup কমান্ড ----------
@bot.command(name="setup", aliases=["SETUP", "Setup")
@commands.has_permissions(administrator=True)  # শুধুমাত্র অ্যাডমিনরা চালাতে পারবে
async def setup(ctx):
    server_id = ctx.guild.id
    channel_id = ctx.channel.id
    registered_channels[server_id] = channel_id
    await ctx.send(f"এই সার্ভারের জন্য এই চ্যানেল (ID: {channel_id}) রেজিস্টার করা হলো। এখন থেকে এই চ্যানেলেই কমান্ড চলবে।")

# ---------- চ্যানেল চেক করার চেক ----------
def is_registered_channel():
    def predicate(ctx):
        server_id = ctx.guild.id
        if server_id not in registered_channels:
            return False  # setup হয় নাই, কাজ করবে না
        # চ্যানেল ম্যাচ করানো হচ্ছে
        return ctx.channel.id == registered_channels[server_id]
    return commands.check(predicate)

@bot.command(name="guilds", aliases=["GUILDS", "Guilds")
async def show_guilds(ctx):
    guild_names = [f"{i+1}. {guild.name}" for i, guild in enumerate(bot.guilds)]
    guild_list = "\n".join(guild_names)
    await ctx.send(f"Le bot est dans les guilds suivantes :\n{guild_list}")

@bot.command(name="lang", aliases=["LANG", "Lang")
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

bot.run(TOKEN)
