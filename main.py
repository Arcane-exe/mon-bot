import discord
from discord.ext import commands
from discord import app_commands
import os, json, re, random, string, asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import threading
from flask import Flask

load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("ERREUR: TOKEN manquant dans les variables d'environnement Render")
    exit(1)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Arcane - ON"
def run_web(): app.run(host="0.0.0.0", port=10000)
threading.Thread(target=run_web, daemon=True).start()

DB_FILE = "db.json"
DEFAULT_DB = {
    "whitelist":[], "antilink":{}, "antispam":{}, "antibot":{},
    "antichannel":{}, "antirole":{}, "antiban":{}, "antikick":{},
    "antiraid":{}, "welcome":{}, "logs":{}, "autorole":{}, "warns":{},
    "gwconfig":{}, "giveaways":{}
}
if not os.path.exists(DB_FILE):
    with open(DB_FILE,"w") as f: json.dump(DEFAULT_DB, f, indent=4)

def get_db():
    try:
        with open(DB_FILE, "r") as f: return json.load(f)
    except: return DEFAULT_DB

def save_db(d):
    with open(DB_FILE,"w") as f: json.dump(d, f, indent=4)

def is_wl(uid): return uid in get_db()["whitelist"]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

join_cache = defaultdict(list)
spam_cache = defaultdict(list)
snipe_cache = {}

def be(embed, interaction=None):
    embed.color = 0x2B2D31
    embed.timestamp = datetime.now()
    if interaction:
        embed.set_footer(text=f"Demandé par {interaction.user}", icon_url=interaction.user.display_avatar.url)
    return embed

@bot.event
async def on_ready():
    print(f"Connecté: {bot.user} | Bot Arcane")
    try: await bot.tree.sync()
    except Exception as e: print(e)

@bot.event
async def on_message_delete(m):
    if m.author.bot: return
    snipe_cache[m.channel.id] = {"content": m.content, "author": m.author, "time": datetime.now()}
    try:
        db=get_db(); gid=str(m.guild.id) if m.guild else None
        if gid and gid in db["logs"]:
            ch = m.guild.get_channel(db["logs"][gid])
            if ch:
                e = discord.Embed(title="🗑️ Message Supprimé", description=f"**Auteur:** {m.author.mention}\n**Salon:** {m.channel.mention}\n**Contenu:**\n{m.content[:1000] or 'Embed/Image'}", color=0xFF4444)
                await ch.send(embed=be(e))
    except: pass

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    db = get_db(); gid = str(message.guild.id)
    if is_wl(message.author.id) or message.author.guild_permissions.administrator:
        await bot.process_commands(message); return

    if db["antilink"].get(gid, {}).get("enabled"):
        if re.search(r"https?://|discord\.gg|discord\.com/invite|discord\.gift", message.content.lower()):
            try:
                await message.delete()
                await message.channel.send(embed=be(discord.Embed(title="🔗 Anti-Lien", description=f"{message.author.mention} lien interdit!")), delete_after=5)
            except: pass
            return

    if db["antispam"].get(gid, {}).get("enabled") or db["antiraid"].get(gid, {}).get("enabled"):
        spam_cache[message.author.id].append(datetime.now())
        spam_cache[message.author.id] = [t for t in spam_cache[message.author.id] if (datetime.now()-t).total_seconds() < 4]
        if len(spam_cache[message.author.id]) > 5:
            try:
                await message.author.timeout(timedelta(minutes=5), reason="AntiSpam")
                await message.channel.send(embed=be(discord.Embed(description=f"{message.author.mention} mute 5min spam")), delete_after=5)
            except: pass

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    db = get_db(); gid = str(member.guild.id)
    if db["antibot"].get(gid, {}).get("enabled"):
        if member.bot and not is_wl(member.id):
            try: await member.ban(reason="AntiBot"); return
            except: pass
    if gid in db["autorole"]:
        try:
            role = member.guild.get_role(db["autorole"][gid])
            if role: await member.add_roles(role)
        except: pass
    if gid in db["welcome"]:
        try:
            ch = member.guild.get_channel(db["welcome"][gid])
            if ch:
                e = discord.Embed(title=f"Bienvenue {member.name} 👋", description=f"Bienvenue {member.mention} sur **{member.guild.name}**\nTu es le **{member.guild.member_count}ème** membre.", color=0x2B2D31)
                e.set_thumbnail(url=member.display_avatar.url)
                await ch.send(embed=e)
        except: pass
    now = datetime.now()
    join_cache[gid].append(now)
    join_cache[gid] = [t for t in join_cache[gid] if (now-t).total_seconds() < 10]
    if len(join_cache[gid]) > 5 and not is_wl(member.id) and db["antiraid"].get(gid, {}).get("enabled"):
        try:
            await member.ban(reason="AntiRaid")
        except: pass

@bot.event
async def on_guild_channel_create(channel):
    db=get_db(); gid=str(channel.guild.id)
    if not db["antichannel"].get(gid, {}).get("enabled"): return
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
        if is_wl(entry.user.id) or entry.user.bot: return
        try: await channel.delete(reason="AntiChannel"); await entry.user.ban(reason="AntiChannel")
        except: pass

@bot.event
async def on_guild_role_create(role):
    db=get_db(); gid=str(role.guild.id)
    if not db["antirole"].get(gid, {}).get("enabled"): return
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        if is_wl(entry.user.id): return
        try: await role.delete(reason="AntiRole"); await entry.user.ban(reason="AntiRole")
        except: pass

@bot.event
async def on_member_ban(guild, user):
    db=get_db(); gid=str(guild.id)
    if not db["antiban"].get(gid, {}).get("enabled"): return
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        if is_wl(entry.user.id): return
        try: await guild.ban(entry.user, reason="AntiBan"); await guild.unban(user, reason="Protection AntiBan")
        except: pass

class HelpSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Choisis une catégorie...", options=[
            discord.SelectOption(label="Protect", emoji="🛡️", description="antilink, antibot, antiraid..."),
            discord.SelectOption(label="Modération", emoji="🔨", description="ban, kick, timeout..."),
            discord.SelectOption(label="Gestion", emoji="⚙️", description="logs, welcome, autorole..."),
            discord.SelectOption(label="Utile", emoji="💎", description="ping, avatar, snipe..."),
        ])
    async def callback(self, interaction: discord.Interaction):
        if self.values[0]=="Protect":
            e = discord.Embed(title="🛡️ Protect", description="```/antilink on/off\n/antispam on/off\n/antibot on/off\n/antichannel on/off\n/antirole on/off\n/antiban on/off\n/antiraid on/off```", color=0x2B2D31)
        elif self.values[0]=="Modération":
            e = discord.Embed(title="🔨 Modération", description="```/ban <membre>\n/kick <membre>\n/timeout <membre> <min>\n/unban <id>\n/clear <nombre>\n/lock /unlock```", color=0x2B2D31)
        elif self.values[0]=="Gestion":
            e = discord.Embed(title="⚙️ Gestion", description="```/whitelist add/remove/list\n/setlogs #salon\n/setwelcome #salon\n/setautorole @role\n/panel```", color=0x2B2D31)
        else:
            e = discord.Embed(title="💎 Utile", description="```/ping\n/avatar\n/serverinfo\n/snipe\n/help```", color=0x2B2D31)
        await interaction.response.edit_message(embed=be(e, interaction))

class HelpView(discord.ui.View):
    def __init__(self): super().__init__(timeout=120); self.add_item(HelpSelect())

class ProtectView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="AntiLink", style=discord.ButtonStyle.gray, emoji="🔗")
    async def al(self, interaction, button):
        db=get_db(); gid=str(interaction.guild.id); db["antilink"].setdefault(gid, {})["enabled"] = not db["antilink"].get(gid,{}).get("enabled",False); save_db(db)
        await interaction.response.send_message(f"AntiLink {'ON' if db['antilink'][gid]['enabled'] else 'OFF'}", ephemeral=True)
    @discord.ui.button(label="AntiBot", style=discord.ButtonStyle.gray, emoji="🤖")
    async def ab(self, interaction, button):
        db=get_db(); gid=str(interaction.guild.id); db["antibot"].setdefault(gid, {})["enabled"] = not db["antibot"].get(gid,{}).get("enabled",False); save_db(db)
        await interaction.response.send_message(f"AntiBot {'ON' if db['antibot'][gid]['enabled'] else 'OFF'}", ephemeral=True)
    @discord.ui.button(label="Activer Tout", style=discord.ButtonStyle.red, emoji="🚨")
    async def all_on(self, interaction, button):
        db=get_db(); gid=str(interaction.guild.id)
        for k in ["antilink","antispam","antibot","antichannel","antirole","antiban","antiraid"]:
            db.setdefault(k, {}).setdefault(gid, {})["enabled"]=True
        save_db(db)
        await interaction.response.send_message("✅ Toutes les protections ON", ephemeral=True)

@bot.tree.command(name="help", description="Panel d'aide")
async def help_cmd(interaction: discord.Interaction):
    e = discord.Embed(title="Bot - Arcane Panel", description="> **Bot Arcane**\n> Anti-Raid, Anti-Link, Anti-Bot\n\nUtilise `/panel` pour activer", color=0x2B2D31)
    e.set_thumbnail(url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=be(e, interaction), view=HelpView())

@bot.tree.command(name="panel", description="Panel protection")
async def panel(interaction: discord.Interaction):
    db=get_db(); gid=str(interaction.guild.id)
    desc = "\n".join([f"**{k}:** {'🟢' if db.get(k,{}).get(gid,{}).get('enabled') else '🔴'}" for k in ["antilink","antispam","antibot","antichannel","antirole","antiban","antiraid"]])
    e = discord.Embed(title="🛡️ Control Panel", description=desc, color=0x2B2D31)
    await interaction.response.send_message(embed=be(e, interaction), view=ProtectView())

@bot.tree.command(name="antilink", description="Toggle antilink")
@app_commands.choices(status=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
async def antilink_cmd(interaction: discord.Interaction, status: str):
    db=get_db(); gid=str(interaction.guild.id); db.setdefault("antilink",{}).setdefault(gid,{})["enabled"]=(status=="on"); save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(description=f"AntiLink **{status.upper()}**"), interaction))

@bot.tree.command(name="antispam", description="Toggle antispam")
@app_commands.choices(status=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
async def antispam_cmd(interaction: discord.Interaction, status: str):
    db=get_db(); gid=str(interaction.guild.id); db.setdefault("antispam",{}).setdefault(gid,{})["enabled"]=(status=="on"); save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(description=f"AntiSpam **{status.upper()}**"), interaction))

@bot.tree.command(name="antibot", description="Toggle antibot")
@app_commands.choices(status=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
async def antibot_cmd(interaction: discord.Interaction, status: str):
    db=get_db(); gid=str(interaction.guild.id); db.setdefault("antibot",{}).setdefault(gid,{})["enabled"]=(status=="on"); save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(description=f"AntiBot **{status.upper()}**"), interaction))

@bot.tree.command(name="antiraid", description="Toggle antiraid")
@app_commands.choices(status=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
async def antiraid_cmd(interaction: discord.Interaction, status: str):
    db=get_db(); gid=str(interaction.guild.id); db.setdefault("antiraid",{}).setdefault(gid,{})["enabled"]=(status=="on"); save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(description=f"AntiRaid **{status.upper()}**"), interaction
                                                     
@bot.tree.command(name="whitelist", description="Whitelist")
@app_commands.choices(action=[app_commands.Choice(name="add", value="add"), app_commands.Choice(name="remove", value="remove"), app_commands.Choice(name="list", value="list")])
async def whitelist_cmd(interaction: discord.Interaction, action: str, membre: discord.Member = None):
    if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("❌ Pas admin", ephemeral=True)
    db=get_db()
    if action=="add" and membre:
        if membre.id not in db["whitelist"]: db["whitelist"].append(membre.id)
        save_db(db); await interaction.response.send_message(embed=be(discord.Embed(description=f"✅ {membre.mention} whitelist"), interaction))
    elif action=="remove" and membre:
        if membre.id in db["whitelist"]: db["whitelist"].remove(membre.id)
        save_db(db); await interaction.response.send_message(embed=be(discord.Embed(description=f"❌ {membre.mention} retiré"), interaction))
    else:
        lst="\n".join([f"<@{uid}> - {uid}" for uid in db["whitelist"]]) or "Vide"
        await interaction.response.send_message(embed=be(discord.Embed(title="Whitelist", description=lst), interaction), ephemeral=True)

@bot.tree.command(name="setlogs", description="Definir salon logs")
async def setlogs(interaction: discord.Interaction, salon: discord.TextChannel):
    db=get_db(); db["logs"][str(interaction.guild.id)]=salon.id; save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(description=f"Logs: {salon.mention}"), interaction))

@bot.tree.command(name="setwelcome", description="Definir welcome")
async def setwelcome(interaction: discord.Interaction, salon: discord.TextChannel):
    db=get_db(); db["welcome"][str(interaction.guild.id)]=salon.id; save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(description=f"Welcome: {salon.mention}"), interaction))

@bot.tree.command(name="setautorole", description="Definir autorole")
async def setautorole(interaction: discord.Interaction, role: discord.Role):
    db=get_db(); db["autorole"][str(interaction.guild.id)]=role.id; save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(description=f"Autorole: {role.mention}"), interaction))

@bot.tree.command(name="ban", description="Bannir")
async def ban_slash(interaction: discord.Interaction, membre: discord.Member, raison: str="Aucune"):
    if is_wl(membre.id): return await interaction.response.send_message("Whitelist", ephemeral=True)
    await membre.ban(reason=raison); await interaction.response.send_message(embed=be(discord.Embed(title="🔨 Ban", description=f"{membre.mention} banni: {raison}"), interaction))

@bot.tree.command(name="ping", description="Ping")
async def ping_slash(interaction: discord.Interaction):
    await interaction.response.send_message(embed=be(discord.Embed(description=f"🏓 {round(bot.latency*1000)}ms"), interaction))

bot.run(TOKEN)
