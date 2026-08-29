import discord
from discord.ext import commands
from discord import app_commands
import os, json, re
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import threading
from flask import Flask

load_dotenv()
TOKEN = os.getenv("TOKEN")

app = Flask(__name__)
@app.route('/')
def home(): return "Protect Bot is ON - Snoway Clone"
def run_web(): app.run(host="0.0.0.0", port=10000)
threading.Thread(target=run_web).start()

DB_FILE = "db.json"
if not os.path.exists(DB_FILE):
    json.dump({"whitelist":[],"antilink":{},"antiraid":{},"welcome":{},"logs":{},"autorole":{},"warns":{}}, open(DB_FILE,"w"))
def get_db(): return json.load(open(DB_FILE))
def save_db(d): json.dump(d, open(DB_FILE,"w"), indent=4)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
join_cache = defaultdict(list)
spam_cache = defaultdict(list)
snipe_cache = {}

def be(embed: discord.Embed, interaction: discord.Interaction = None):
    embed.color = 0x2B2D31
    embed.timestamp = datetime.now()
    if interaction:
        embed.set_footer(text=f"Demandé par {interaction.user}", icon_url=interaction.user.display_avatar.url)
    return embed
def is_wl(uid): return uid in get_db()["whitelist"]

@bot.event
async def on_ready():
    print(f"Connecté : {bot.user} - Protect Clean")
    await bot.tree.sync()

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    snipe_cache[message.channel.id] = {"content": message.content, "author": message.author, "time": datetime.now()}
    # LOGS auto
    try:
        db=get_db()
        gid=str(message.guild.id) if message.guild else None
        if gid and gid in db["logs"]:
            ch = message.guild.get_channel(db["logs"][gid])
            if ch:
                e = discord.Embed(title="🗑️ Message Supprimé", description=f"**Auteur:** {message.author.mention}\n**Salon:** {message.channel.mention}\n**Contenu:**\n{message.content[:1000] or 'Aucun / Embed'}", color=0xFF4444)
                await ch.send(embed=be(e))
    except: pass

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    db = get_db()
    gid = str(message.guild.id)
    if is_wl(message.author.id) or message.author.guild_permissions.administrator:
        await bot.process_commands(message)
        return
    if db["antilink"].get(gid, {}).get("enabled"):
        if re.search(r"https?://|discord\.gg|discord\.com/invite", message.content.lower()):
            try:
                await message.delete()
                e = be(discord.Embed(title="🔗 Anti-Lien", description=f"{message.author.mention} Les liens sont interdits."))
                await message.channel.send(embed=e, delete_after=5)
            except: pass
            return
    if db["antiraid"].get(gid, {}).get("enabled"):
        spam_cache[message.author.id].append(datetime.now())
        spam_cache[message.author.id] = [t for t in spam_cache[message.author.id] if (datetime.now()-t).seconds < 4]
        if len(spam_cache[message.author.id]) > 5:
            try:
                await message.author.timeout(timedelta(minutes=5), reason="Anti-Spam")
                e = be(discord.Embed(title="🛡️ Anti-Spam", description=f"{message.author.mention} a été mute 5min pour spam."))
                await message.channel.send(embed=e, delete_after=5)
            except: pass
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    db = get_db()
    gid = str(member.guild.id)

    if gid in db["autorole"]:
        try:
            role = member.guild.get_role(db["autorole"][gid])
            if role: await member.add_roles(role)
        except: pass

    if gid in db["welcome"]:
        try:
            ch = member.guild.get_channel(db["welcome"][gid])
            if ch:
                e = discord.Embed(title=f"Bienvenue {member.name} 👋", description=f"Bienvenue {member.mention} sur **{member.guild.name}**!\n\nTu es le **{member.guild.member_count}ème** membre.", color=0x2B2D31)
                e.set_thumbnail(url=member.display_avatar.url)
                await ch.send(embed=e)
        except: pass

    if not db["antiraid"].get(gid, {}).get("enabled"): return
    now = datetime.now()
    join_cache[gid].append(now)
    join_cache[gid] = [t for t in join_cache[gid] if (now - t).seconds < 10]
    if len(join_cache[gid]) > 5:
        if is_wl(member.id): return
        try:
            await member.ban(reason="Protect: Raid détecté")
            e = be(discord.Embed(title="🚨 Raid Détecté", description=f"**{member}** a été banni.\n> {len(join_cache[gid])} joins en 10s\nLockdown activé."))
            e.color = 0xFF4444
            for ch in member.guild.text_channels[:3]:
                try: await ch.send(embed=e)
                except: pass
            for ch in member.guild.channels:
                try: await ch.set_permissions(member.guild.default_role, send_messages=False)
                except: pass
        except: pass

class HelpSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Choisis une catégorie...", options=[
            discord.SelectOption(label="Modération", emoji="🔨", description="ban, kick, timeout..."),
            discord.SelectOption(label="Protect", emoji="🛡️", description="whitelist, anti-raid, anti-lien"),
            discord.SelectOption(label="Gestion", emoji="⚙️", description="logs, welcome, autorole"),
            discord.SelectOption(label="Utile", emoji="💎", description="info, avatar, snipe"),
        ])
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Modération":
            e = be(discord.Embed(title="🔨 Modération", description="`/ban` `membre raison`\n`/kick`\n`/timeout` `membre minutes`\n`/clear` `nombre`\n`/lock` `/unlock`"), interaction)
        elif self.values[0] == "Protect":
            e = be(discord.Embed(title="🛡️ Protect", description="`/whitelist add/remove/list`\n`/antilink on/off`\n`/antiraid on/off`\nBypass auto si whitelist ou admin"), interaction)
        elif self.values[0] == "Gestion":
            e = be(discord.Embed(title="⚙️ Gestion", description="`/setwelcome #salon`\n`/setlogs #salon`\n`/setautorole @role`"), interaction)
        else:
            e = be(discord.Embed(title="💎 Utile", description="`/serverinfo`\n`/snipe`\n`/ping`\n`/avatar`"), interaction)
        await interaction.response.edit_message(embed=e)

class HelpView(discord.ui.View):
    def __init__(self): super().__init__(timeout=60); self.add_item(HelpSelect())

@bot.tree.command(name="help", description="Menu d'aide du bot protect")
async def help_cmd(interaction: discord.Interaction):
    e = be(discord.Embed(title="🛡️ Protect Bot - Panel", description="Un bot protect clean, rapide et sécurisé.\n\n**Sélectionne une catégorie ci-dessous**\n\n> Anti-Raid • Anti-Lien • Anti-Spam • Whitelist"), interaction)
    e.set_thumbnail(url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=e, view=HelpView())

@bot.tree.command(name="whitelist", description="Gérer la whitelist")
@app_commands.choices(action=[app_commands.Choice(name="add", value="add"), app_commands.Choice(name="remove", value="remove"), app_commands.Choice(name="list", value="list")])
async def whitelist(interaction: discord.Interaction, action: str, membre: discord.Member = None):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message(embed=be(discord.Embed(description="❌ Pas admin")), ephemeral=True)
    db = get_db()
    if action == "add" and membre:
        if membre.id not in db["whitelist"]: db["whitelist"].append(membre.id)
        save_db(db)
        await interaction.response.send_message(embed=be(discord.Embed(title="✅ Whitelist", description=f"{membre.mention} ajouté."), interaction))
    elif action == "remove" and membre:
        if membre.id in db["whitelist"]: db["whitelist"].remove(membre.id)
        save_db(db)
        await interaction.response.send_message(embed=be(discord.Embed(title="❌ Whitelist", description=f"{membre.mention} retiré."), interaction))
    else:
        lst = "\n".join([f"<@{uid}> - `{uid}`" for uid in db["whitelist"]]) or "Aucun"
        await interaction.response.send_message(embed=be(discord.Embed(title="📋 Whitelist", description=lst), interaction), ephemeral=True)

@bot.tree.command(name="antilink", description="Activer l'anti-lien")
@app_commands.choices(status=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
async def antilink(interaction: discord.Interaction, status: str):
    db = get_db(); gid=str(interaction.guild.id)
    if gid not in db["antilink"]: db["antilink"][gid]={}
    db["antilink"][gid]["enabled"]=(status=="on"); save_db(db)
    e = be(discord.Embed(title="🔗 Anti-Lien", description=f"Anti-lien **{status.upper()}**"), interaction)
    e.color = 0x00FF88 if status=="on" else 0xFF4444
    await interaction.response.send_message(embed=e)

@bot.tree.command(name="antiraid", description="Activer l'anti-raid")
@app_commands.choices(status=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
async def antiraid(interaction: discord.Interaction, status: str):
    db=get_db(); gid=str(interaction.guild.id)
    if gid not in db["antiraid"]: db["antiraid"][gid]={}
    db["antiraid"][gid]["enabled"]=(status=="on"); save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(title="🛡️ Anti-Raid", description=f"Anti-Raid **{status.upper()}**"), interaction))

@bot.tree.command(name="setlogs", description="Définir le salon des logs")
async def setlogs(interaction: discord.Interaction, salon: discord.TextChannel):
    db=get_db(); gid=str(interaction.guild.id); db["logs"][gid]=salon.id; save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(title="✅ Logs", description=f"Logs définis sur {salon.mention}"), interaction))

@bot.tree.command(name="setwelcome", description="Définir le salon de bienvenue")
async def setwelcome(interaction: discord.Interaction, salon: discord.TextChannel):
    db=get_db(); gid=str(interaction.guild.id); db["welcome"][gid]=salon.id; save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(title="✅ Welcome", description=f"Welcome défini sur {salon.mention}"), interaction))

@bot.tree.command(name="setautorole", description="Définir l'autorole")
async def setautorole(interaction: discord.Interaction, role: discord.Role):
    db=get_db(); gid=str(interaction.guild.id); db["autorole"][gid]=role.id; save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(title="✅ Autorole", description=f"Autorole défini sur {role.mention}"), interaction))

@bot.tree.command(name="ban", description="Bannir un membre")
async def ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison"):
    if is_wl(membre.id): return await interaction.response.send_message(embed=be(discord.Embed(description="❌ Whitelist, impossible.")), ephemeral=True)
    await membre.ban(reason=raison)
    e = be(discord.Embed(title="🔨 Ban", description=f"**Membre:** {membre.mention}\n**Raison:** {raison}"), interaction); e.color = 0xFF4444
    await interaction.response.send_message(embed=e)

@bot.tree.command(name="kick", description="Expulser un membre")
async def kick(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison"):
    await membre.kick(reason=raison)
    await interaction.response.send_message(embed=be(discord.Embed(title="👢 Kick", description=f"{membre.mention} kick pour: {raison}"), interaction))

@bot.tree.command(name="timeout", description="Mute un membre")
async def timeout_cmd(interaction: discord.Interaction, membre: discord.Member, minutes: int, raison: str = "Spam"):
    await membre.timeout(timedelta(minutes=minutes), reason=raison)
    await interaction.response.send_message(embed=be(discord.Embed(title="🔇 Timeout", description=f"{membre.mention} mute **{minutes}min**\nRaison: {raison}"), interaction))

@bot.tree.command(name="clear", description="Clear messages")
async def clear(interaction: discord.Interaction, nombre: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    await interaction.followup.send(embed=be(discord.Embed(description=f"✅ **{len(deleted)}** messages supprimés."), interaction), ephemeral=True)

@bot.tree.command(name="lock", description="Vérouiller le salon")
async def lock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(embed=be(discord.Embed(title="🔒 Vérouillé", description=f"{interaction.channel.mention} vérouillé."), interaction))

@bot.tree.command(name="unlock", description="Déverrouiller le salon")
async def unlock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message(embed=be(discord.Embed(title="🔓 Déverrouillé", description=f"{interaction.channel.mention} déverrouillé."), interaction))

@bot.tree.command(name="serverinfo", description="Infos serveur")
async def serverinfo(interaction: discord.Interaction):
    g=interaction.guild
    e = be(discord.Embed(title=f"💎 {g.name}", description=f"**Owner:** <@{g.owner_id}>\n**Membres:** {g.member_count}\n**Boosts:** {g.premium_subscription_count}"), interaction)
    e.set_thumbnail(url=g.icon.url if g.icon else None)
    await interaction.response.send_message(embed=e)

@bot.tree.command(name="snipe", description="Voir le dernier message supprimé")
async def snipe(interaction: discord.Interaction):
    data = snipe_cache.get(interaction.channel.id)
    if not data: return await interaction.response.send_message(embed=be(discord.Embed(description="Rien à snipe")), ephemeral=True)
    e = be(discord.Embed(title="🗑️ Snipe", description=data["content"]), interaction)
    e.set_author(name=str(data["author"]), icon_url=data["author"].display_avatar.url)
    await interaction.response.send_message(embed=e)

@bot.tree.command(name="avatar", description="Avatar d'un membre")
async def avatar(interaction: discord.Interaction, membre: discord.Member = None):
    m = membre or interaction.user
    e = be(discord.Embed(title=f"Avatar de {m.name}", description=f"[Lien direct]({m.display_avatar.url})"), interaction)
    e.set_image(url=m.display_avatar.url)
    await interaction.response.send_message(embed=e)

@bot.tree.command(name="ping", description="Ping du bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(embed=be(discord.Embed(description=f"🏓 **{round(bot.latency*1000)}ms**"), interaction))

bot.run(TOKEN)
