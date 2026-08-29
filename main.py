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
def home(): return "Bot Arcane - ON"
def run_web(): app.run(host="0.0.0.0", port=10000)
threading.Thread(target=run_web).start()

DB_FILE = "db.json"
if not os.path.exists(DB_FILE):
    json.dump({
        "whitelist":[], "antilink":{}, "antispam":{}, "antibot":{},
        "antichannel":{}, "antirole":{}, "antiban":{}, "antikick":{},
        "antiraid":{}, "welcome":{}, "logs":{}, "autorole":{}, "warns":{},
        "gwconfig":{}, "giveaways":{}
    }, open(DB_FILE,"w"))
def get_db(): return json.load(open(DB_FILE))
def save_db(d): json.dump(d, open(DB_FILE,"w"), indent=4)
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
    await bot.tree.sync()

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
        spam_cache[message.author.id] = [t for t in spam_cache[message.author.id] if (datetime.now()-t).seconds < 4]
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
    join_cache[gid] = [t for t in join_cache[gid] if (now-t).seconds < 10]
    if len(join_cache[gid]) > 5 and not is_wl(member.id) and db["antiraid"].get(gid, {}).get("enabled"):
        try:
            await member.ban(reason="AntiRaid")
            for c in member.guild.channels:
                try: await c.set_permissions(member.guild.default_role, send_messages=False)
                except: pass
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
async def on_guild_channel_delete(channel):
    db=get_db(); gid=str(channel.guild.id)
    if not db["antichannel"].get(gid, {}).get("enabled"): return
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        if is_wl(entry.user.id): return
        try: await entry.user.ban(reason="AntiChannel Delete")
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
async def on_guild_role_delete(role):
    db=get_db(); gid=str(role.guild.id)
    if not db["antirole"].get(gid, {}).get("enabled"): return
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        if is_wl(entry.user.id): return
        try: await entry.user.ban(reason="AntiRole Delete")
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
            discord.SelectOption(label="Protect", emoji="🛡️", description="antilink, antibot, antiraid, antichannel..."),
            discord.SelectOption(label="Modération", emoji="🔨", description="ban, kick, timeout, clear, lock"),
            discord.SelectOption(label="Gestion", emoji="⚙️", description="logs, welcome, autorole, whitelist"),
            discord.SelectOption(label="Utile", emoji="💎", description="ping, avatar, serverinfo, snipe"),
        ])
    async def callback(self, interaction: discord.Interaction):
        if self.values[0]=="Protect":
            e = discord.Embed(title="🛡️ Protect - Arcane", description="```/antilink on/off\n/antispam on/off\n/antibot on/off\n/antichannel on/off\n/antirole on/off\n/antiban on/off\n/antikick on/off\n/antiraid on/off```\nBypass si whitelist/admin")
        elif self.values[0]=="Modération":
            e = discord.Embed(title="🔨 Modération", description="```/ban <membre> [raison]\n/kick <membre>\n/timeout <membre> <min>\n/unban <id>\n/clear <nombre>\n/lock\n/unlock\n/warn```")
        elif self.values[0]=="Gestion":
            e = discord.Embed(title="⚙️ Gestion", description="```/whitelist add/remove/list\n/setlogs #salon\n/setwelcome #salon\n/setautorole @role\n/panel```")
        else:
            e = discord.Embed(title="💎 Utile", description="```/ping\n/avatar [membre]\n/serverinfo\n/snipe\n/help```")
        await interaction.response.edit_message(embed=be(e, interaction))

class HelpView(discord.ui.View):
    def __init__(self): super().__init__(timeout=120); self.add_item(HelpSelect())

class ProtectView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="AntiLink", style=discord.ButtonStyle.gray, emoji="🔗")
    async def al(self, interaction, button):
        db=get_db(); gid=str(interaction.guild.id); enabled=not db["antilink"].get(gid,{}).get("enabled",False)
        if gid not in db["antilink"]: db["antilink"][gid]={}
        db["antilink"][gid]["enabled"]=enabled; save_db(db)
        await interaction.response.send_message(f"AntiLink {'ON' if enabled else 'OFF'}", ephemeral=True)
    @discord.ui.button(label="AntiBot", style=discord.ButtonStyle.gray, emoji="🤖")
    async def ab(self, interaction, button):
        db=get_db(); gid=str(interaction.guild.id); enabled=not db["antibot"].get(gid,{}).get("enabled",False)
        if gid not in db["antibot"]: db["antibot"][gid]={}
        db["antibot"][gid]["enabled"]=enabled; save_db(db)
        await interaction.response.send_message(f"AntiBot {'ON' if enabled else 'OFF'}", ephemeral=True)
    @discord.ui.button(label="Activer Tout", style=discord.ButtonStyle.red, emoji="🚨")
    async def all_on(self, interaction, button):
        db=get_db(); gid=str(interaction.guild.id)
        for k in ["antilink","antispam","antibot","antichannel","antirole","antiban","antikick","antiraid"]:
            if gid not in db[k]: db[k][gid]={}
            db[k][gid]["enabled"]=True
        save_db(db)
        await interaction.response.send_message("✅ Toutes les protections ON", ephemeral=True)

@bot.tree.command(name="help", description="Panel d'aide")
async def help_cmd(interaction: discord.Interaction):
    e = discord.Embed(title="Bot - Arcane Panel", description="> **Bot Arcane**\n> Anti-Raid, Anti-Link, Anti-Bot, Anti-Channel/Role/Ban\n\n`🛡️` Protect\n`🔨` Modération\n`⚙️` Gestion\n`💎` Utile\n\nUtilise `/panel` pour activer les protections", color=0x2B2D31)
    e.set_thumbnail(url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=be(e, interaction), view=HelpView())

@bot.tree.command(name="panel", description="Panel protection")
async def panel(interaction: discord.Interaction):
    db=get_db(); gid=str(interaction.guild.id)
    desc = f"**AntiLink:** {'🟢' if db['antilink'].get(gid,{}).get('enabled') else '🔴'}\n**AntiSpam:** {'🟢' if db['antispam'].get(gid,{}).get('enabled') else '🔴'}\n**AntiBot:** {'🟢' if db['antibot'].get(gid,{}).get('enabled') else '🔴'}\n**AntiChannel:** {'🟢' if db['antichannel'].get(gid,{}).get('enabled') else '🔴'}\n**AntiRole:** {'🟢' if db['antirole'].get(gid,{}).get('enabled') else '🔴'}\n**AntiBan:** {'🟢' if db['antiban'].get(gid,{}).get('enabled') else '🔴'}\n**AntiRaid:** {'🟢' if db['antiraid'].get(gid,{}).get('enabled') else '🔴'}"
    e = discord.Embed(title="🛡️ Control Panel", description=desc, color=0x2B2D31)
    await interaction.response.send_message(embed=be(e, interaction), view=ProtectView())

def make_toggle(name, key):
    @bot.tree.command(name=name, description=f"Toggle {name}")
    @app_commands.choices(status=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
    async def cmd(interaction: discord.Interaction, status: str):
        db=get_db(); gid=str(interaction.guild.id)
        if gid not in db[key]: db[key][gid]={}
        db[key][gid]["enabled"]=(status=="on"); save_db(db)
        await interaction.response.send_message(embed=be(discord.Embed(title=f"🛡️ {name}", description=f"{name} **{status.upper()}**"), interaction))
    return cmd

make_toggle("antilink","antilink")
make_toggle("antispam","antispam")
make_toggle("antibot","antibot")
make_toggle("antichannel","antichannel")
make_toggle("antirole","antirole")
make_toggle("antiban","antiban")
make_toggle("antikick","antikick")
make_toggle("antiraid","antiraid")

@bot.tree.command(name="whitelist", description="Whitelist")
@app_commands.choices(action=[app_commands.Choice(name="add", value="add"), app_commands.Choice(name="remove", value="remove"), app_commands.Choice(name="list", value="list")])
async def whitelist(interaction: discord.Interaction, action: str, membre: discord.Member = None):
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

@bot.tree.command(name="setlogs", description="Logs")
async def setlogs(interaction: discord.Interaction, salon: discord.TextChannel):
    db=get_db(); db["logs"][str(interaction.guild.id)]=salon.id; save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(description=f"Logs: {salon.mention}"), interaction))

@bot.tree.command(name="setwelcome", description="Welcome")
async def setwelcome(interaction: discord.Interaction, salon: discord.TextChannel):
    db=get_db(); db["welcome"][str(interaction.guild.id)]=salon.id; save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(description=f"Welcome: {salon.mention}"), interaction))

@bot.tree.command(name="setautorole", description="Autorole")
async def setautorole(interaction: discord.Interaction, role: discord.Role):
    db=get_db(); db["autorole"][str(interaction.guild.id)]=role.id; save_db(db)
    await interaction.response.send_message(embed=be(discord.Embed(description=f"Autorole: {role.mention}"), interaction))

@bot.tree.command(name="ban", description="Bannir")
async def ban_slash(interaction: discord.Interaction, membre: discord.Member, raison: str="Aucune"):
    if is_wl(membre.id): return await interaction.response.send_message("Whitelist", ephemeral=True)
    await membre.ban(reason=raison); await interaction.response.send_message(embed=be(discord.Embed(title="🔨 Ban", description=f"{membre.mention} banni: {raison}"), interaction))

@bot.tree.command(name="kick", description="Kick")
async def kick_slash(interaction: discord.Interaction, membre: discord.Member, raison: str="Aucune"):
    await membre.kick(reason=raison); await interaction.response.send_message(embed=be(discord.Embed(description=f"{membre.mention} kick"), interaction))

@bot.tree.command(name="timeout", description="Timeout")
async def timeout_slash(interaction: discord.Interaction, membre: discord.Member, minutes: int, raison: str="Spam"):
    await membre.timeout(timedelta(minutes=minutes), reason=raison); await interaction.response.send_message(embed=be(discord.Embed(description=f"{membre.mention} mute {minutes}min"), interaction))

@bot.tree.command(name="clear", description="Clear")
async def clear_slash(interaction: discord.Interaction, nombre: int):
    await interaction.response.defer(ephemeral=True)
    d = await interaction.channel.purge(limit=nombre)
    await interaction.followup.send(f"✅ {len(d)} messages supprimés", ephemeral=True)

@bot.tree.command(name="lock", description="Lock")
async def lock_slash(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(embed=be(discord.Embed(title="🔒 Vérouillé"), interaction))

@bot.tree.command(name="unlock", description="Unlock")
async def unlock_slash(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message(embed=be(discord.Embed(title="🔓 Déverrouillé"), interaction))

@bot.tree.command(name="avatar", description="Avatar")
async def avatar_slash(interaction: discord.Interaction, membre: discord.Member = None):
    m=membre or interaction.user
    e=discord.Embed(title=f"Avatar {m.name}", color=0x2B2D31); e.set_image(url=m.display_avatar.url)
    await interaction.response.send_message(embed=be(e, interaction))

@bot.tree.command(name="snipe", description="Snipe")
async def snipe_slash(interaction: discord.Interaction):
    data=snipe_cache.get(interaction.channel.id)
    if not data: return await interaction.response.send_message("Rien à snipe", ephemeral=True)
    e=discord.Embed(title="Snipe", description=data["content"], color=0x2B2D31); e.set_author(name=str(data["author"]), icon_url=data["author"].display_avatar.url)
    await interaction.response.send_message(embed=e)

@bot.tree.command(name="serverinfo", description="Infos")
async def serverinfo_slash(interaction: discord.Interaction):
    g=interaction.guild; e=discord.Embed(title=g.name, description=f"Owner: <@{g.owner_id}>\nMembres: {g.member_count}\nBoosts: {g.premium_subscription_count}", color=0x2B2D31)
    e.set_thumbnail(url=g.icon.url if g.icon else None)
    await interaction.response.send_message(embed=be(e, interaction))

@bot.tree.command(name="ping", description="Ping")
async def ping_slash(interaction: discord.Interaction):
    await interaction.response.send_message(embed=be(discord.Embed(description=f"🏓 {round(bot.latency*1000)}ms"), interaction))

@bot.tree.command(name="warn", description="Warn un membre")
async def warn_slash(interaction: discord.Interaction, membre: discord.Member, raison: str="Aucune"):
    try: await membre.send(f"⚠️ Warn sur {interaction.guild.name}: {raison}")
    except: pass
    await interaction.response.send_message(embed=be(discord.Embed(description=f"⚠️ {membre.mention} warn: {raison}"), interaction))

@bot.tree.command(name="unban", description="Unban par ID")
async def unban_slash(interaction: discord.Interaction, user_id: str):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user); await interaction.response.send_message(f"🔓 {user} débanni")
    except: await interaction.response.send_message("❌ Introuvable", ephemeral=True)

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_p(ctx, member: discord.Member, *, reason=None):
    if not is_wl(member.id): await member.ban(reason=reason); await ctx.send(f"🔨 {member} banni")

import random, string, asyncio

def gen_code(): return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_gw_config(gid):
    db=get_db()
    if str(gid) not in db["gwconfig"]:
        db["gwconfig"][str(gid)] = {
            "prix": "Nitro x1", "dure": 600000, "emoji": "🎉",
            "salon": None, "wins": 1, "roleinterdit": [], "rolerequis": [], "vocal": False
        }
        save_db(db)
    return db["gwconfig"][str(gid)]

def format_dure(ms):
    s = ms // 1000
    if s < 60: return f"{s}s"
    m = s // 60
    if m < 60: return f"{m}m"
    h = m // 60
    if h < 24: return f"{h}h {m%60}m"
    d = h // 24
    return f"{d}j {h%24}h"

class GiveawayConfigSelect(discord.ui.Select):
    def __init__(self, guild_id):
        self.gid = guild_id
        super().__init__(placeholder="Modifier un paramètre...", options=[
            discord.SelectOption(label="Gain", emoji="🎁", value="gain"),
            discord.SelectOption(label="Durée", emoji="⏱️", value="duree"),
            discord.SelectOption(label="Salon", emoji="🏷️", value="salon"),
            discord.SelectOption(label="Emoji", emoji="🎉", value="emoji"),
            discord.SelectOption(label="Rôle obligatoire", emoji="⛓️", value="obligatoire"),
            discord.SelectOption(label="Rôle interdit", emoji="🚫", value="interdit"),
            discord.SelectOption(label="Vocal obligatoire", emoji="🔊", value="vocal"),
        ])
    async def callback(self, interaction: discord.Interaction):
        cfg = get_gw_config(self.gid)
        if self.values[0] == "vocal":
            cfg["vocal"] = not cfg["vocal"]
            db=get_db(); db["gwconfig"][str(self.gid)]=cfg; save_db(db)
            return await interaction.response.edit_message(embed=await build_gw_embed(interaction.guild), view=GiveawaySetupView(self.gid))

        await interaction.response.send_modal(GiveawayModal(self.values[0], self.gid))

class GiveawayModal(discord.ui.Modal):
    def __init__(self, field, gid):
        super().__init__(title=f"Modifier {field}")
        self.field = field; self.gid = gid
        self.input = discord.ui.TextInput(label=f"Nouvelle valeur pour {field}", placeholder="Ex: Nitro x1 ou 1h ou #giveaway", required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = get_gw_config(self.gid); db=get_db()
        val = self.input.value
        if self.field == "gain": cfg["prix"] = val
        elif self.field == "duree":
            import re
            m = re.match(r"(\d+)([smhj])", val.lower())
            if not m: return await interaction.response.send_message("Format invalide. Ex: 10m, 1h, 2j", ephemeral=True)
            num, unit = int(m.group(1)), m.group(2)
            mult = {"s":1, "m":60, "h":3600, "j":86400}[unit]
            cfg["dure"] = num * mult * 1000
        elif self.field == "salon":
            ch_id = int(re.sub(r"[<#>]","", val)) if val.startswith("<#") else int(val) if val.isdigit() else None
            if not ch_id:
                try: ch_id = interaction.guild.get_channel(int(val.replace("<#","").replace(">",""))).id
                except: return await interaction.response.send_message("Salon invalide mentionne #salon", ephemeral=True)
            cfg["salon"] = ch_id
        elif self.field == "emoji": cfg["emoji"] = val
        elif self.field in ["obligatoire","interdit"]:
            role_id = int(val.replace("<@&","").replace(">","")) if "<@&" in val else int(val) if val.isdigit() else None
            if not role_id: return await interaction.response.send_message("Mentionne un rôle @role", ephemeral=True)
            key = "rolerequis" if self.field=="obligatoire" else "roleinterdit"
            if role_id in cfg[key]: cfg[key].remove(role_id)
            else: cfg[key].append(role_id)

        db["gwconfig"][str(self.gid)] = cfg; save_db(db)
        await interaction.response.edit_message(embed=await build_gw_embed(interaction.guild), view=GiveawaySetupView(self.gid))

async def build_gw_embed(guild):
    cfg = get_gw_config(guild.id)
    salon = guild.get_channel(cfg["salon"]) if cfg["salon"] else None
    req = ", ".join([f"<@&{r}>" for r in cfg["rolerequis"]]) or "Aucun"
    inter = ", ".join([f"<@&{r}>" for r in cfg["roleinterdit"]]) or "Aucun"
    e = discord.Embed(title="🎉 Bot Arcane - Giveaway Config", description=f"Configure ton giveaway puis lance-le", color=0x2B2D31)
    e.add_field(name="🎁 Gain", value=f"```{cfg['prix']}```", inline=True)
    e.add_field(name="⏱️ Durée", value=f"```{format_dure(cfg['dure'])}```", inline=True)
    e.add_field(name="🏷️ Salon", value=f"```{salon.name if salon else 'Non configuré'}```", inline=True)
    e.add_field(name="⛓️ Rôle requis", value=req, inline=True)
    e.add_field(name="🚫 Rôle interdit", value=inter, inline=True)
    e.add_field(name="🔊 Vocal requis", value=f"{'✅' if cfg['vocal'] else '❌'}", inline=True)
    e.add_field(name="Emoji", value=cfg["emoji"], inline=True)
    e.set_footer(text="Bot Arcane • Giveaway")
    return be(e)

class GiveawaySetupView(discord.ui.View):
    def __init__(self, gid):
        super().__init__(timeout=300); self.gid=gid
        self.add_item(GiveawayConfigSelect(gid))
    @discord.ui.button(label="Lancer le giveaway", style=discord.ButtonStyle.success, emoji="🚀")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_gw_config(self.gid)
        if not cfg["salon"]: return await interaction.response.send_message("❌ Configure le salon d'abord!", ephemeral=True)
        channel = interaction.guild.get_channel(cfg["salon"])
        if not channel: return await interaction.response.send_message("❌ Salon introuvable", ephemeral=True)

        code = gen_code()
        end_ts = datetime.now() + timedelta(milliseconds=cfg["dure"])

        embed = discord.Embed(title=f"🎉 Giveaway: {cfg['prix']}", description=f"Réagis avec {cfg['emoji']} pour participer!\n**Gagnants:** {cfg['wins']}\n**Fin:** <t:{int(end_ts.timestamp())}:R>", color=0x2B2D31)
        embed.set_footer(text=f"Bot Arcane • Code: {code}")

        view = GiveawayJoinView(code)
        msg = await channel.send(embed=embed, view=view)

        db=get_db()
        gw = {
            "code": code, "messageId": msg.id, "channelId": channel.id, "guildId": str(self.gid),
            "prix": cfg["prix"], "endTime": end_ts.timestamp(), "ended": False,
            "participants": [], "rolerequis": cfg["rolerequis"], "roleinterdit": cfg["roleinterdit"],
            "vocal": cfg["vocal"], "author": interaction.user.id
        }
        if "giveaways" not in db: db["giveaways"]={}
        db["giveaways"][code]=gw; save_db(db)

        await interaction.response.send_message(f"✅ Giveaway lancé dans {channel.mention} [Lien](https://discord.com/channels/{self.gid}/{channel.id}/{msg.id})", ephemeral=True)
        bot.loop.create_task(giveaway_scheduler(code))

class GiveawayJoinView(discord.ui.View):
    def __init__(self, code):
        super().__init__(timeout=None)
        self.code = code
    @discord.ui.button(label="Participer", style=discord.ButtonStyle.primary, emoji="🎉", custom_id="gw_join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        db=get_db(); gw=db["giveaways"].get(self.code)
        if not gw or gw["ended"]: return await interaction.response.send_message("Giveaway terminé", ephemeral=True)
        # checks rôles
        if gw["rolerequis"] and not any(r.id in gw["rolerequis"] for r in interaction.user.roles):
            return await interaction.response.send_message("❌ Il te manque un rôle requis", ephemeral=True)
        if any(r.id in gw["roleinterdit"] for r in interaction.user.roles):
            return await interaction.response.send_message("❌ Tu as un rôle interdit", ephemeral=True)
        if gw["vocal"] and not interaction.user.voice:
            return await interaction.response.send_message("❌ Tu dois être en vocal", ephemeral=True)
        if interaction.user.id in gw["participants"]:
            return await interaction.response.send_message("Tu participes déjà!", ephemeral=True)

        gw["participants"].append(interaction.user.id)
        db["giveaways"][self.code]=gw; save_db(db)
        await interaction.response.send_message(f"✅ Tu participes pour **{gw['prix']}**!", ephemeral=True)

    @discord.ui.button(label="Participants", style=discord.ButtonStyle.secondary, custom_id="gw_list")
    async def list_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        db=get_db(); gw=db["giveaways"].get(self.code)
        if not gw: return
        count = len(gw["participants"])
        await interaction.response.send_message(f"👥 **{count}** participants", ephemeral=True)

class PersistentGiveawayView(discord.ui.View):
    def __init__(self, code):
        super().__init__(timeout=None)
        self.code = code
        self.add_item(discord.ui.Button(label="Participer", style=discord.ButtonStyle.primary, emoji="🎉", custom_id=f"giveaway_entry_{code}"))
        self.add_item(discord.ui.Button(label="Participants", style=discord.ButtonStyle.secondary, custom_id=f"giveaway_list_{code}"))

async def giveaway_scheduler(code):
    while True:
        await asyncio.sleep(10)
        db=get_db(); gw=db["giveaways"].get(code)
        if not gw or gw["ended"]: return
        if datetime.now().timestamp() >= gw["endTime"]:
            channel = bot.get_channel(gw["channelId"])
            if channel:
                try:
                    msg = await channel.fetch_message(gw["messageId"])
                    if not gw["participants"]:
                        e = discord.Embed(title="🎉 Giveaway terminé", description=f"**{gw['prix']}**\nAucun participant", color=0xFF4444)
                        await msg.edit(embed=e, view=None)
                        await channel.send(f"Aucun gagnant pour **{gw['prix']}**")
                    else:
                        winner_id = random.choice(gw["participants"])
                        winner = channel.guild.get_member(winner_id)
                        e = discord.Embed(title="🎉 Giveaway terminé", description=f"**{gw['prix']}**\nGagnant: {winner.mention if winner else f'<@{winner_id}>'}", color=0x00FF88)
                        await msg.edit(embed=e, view=None)
                        await channel.send(f"🎉 Bravo {winner.mention if winner else f'<@{winner_id}>'} tu as gagné **{gw['prix']}**!")
                except: pass
            gw["ended"]=True; db["giveaways"][code]=gw; save_db(db)
            return

@bot.tree.command(name="giveaway", description="Configurer un giveaway")
async def giveaway_cmd(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("❌ Permission Manage Server requise", ephemeral=True)
    e = await build_gw_embed(interaction.guild)
    await interaction.response.send_message(embed=e, view=GiveawaySetupView(interaction.guild.id))

@bot.tree.command(name="greroll", description="Retirer un gagnant giveaway")
async def greroll(interaction: discord.Interaction, code: str):
    db=get_db(); gw=db["giveaways"].get(code.upper())
    if not gw: return await interaction.response.send_message("Code invalide", ephemeral=True)
    if not gw["participants"]: return await interaction.response.send_message("Pas de participants", ephemeral=True)
    winner_id = random.choice(gw["participants"])
    await interaction.response.send_message(f"🎉 Nouveau gagnant: <@{winner_id}> pour **{gw['prix']}**")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        cid = interaction.data.get("custom_id","")
        if cid.startswith("giveaway_entry_"):
            code = cid.replace("giveaway_entry_","")
            db=get_db(); gw=db["giveaways"].get(code)
            if not gw: return
            if gw["rolerequis"] and not any(r.id in gw["rolerequis"] for r in interaction.user.roles):
                return await interaction.response.send_message("❌ Rôle requis manquant", ephemeral=True)
            if interaction.user.id in gw["participants"]:
                return await interaction.response.send_message("Déjà inscrit", ephemeral=True)
            gw["participants"].append(interaction.user.id)
            db["giveaways"][code]=gw; save_db(db)
            await interaction.response.send_message(f"✅ Inscrit pour {gw['prix']}", ephemeral=True)
        elif cid.startswith("giveaway_list_"):
            code = cid.replace("giveaway_list_","")
            db=get_db(); gw=db["giveaways"].get(code)
            if gw: await interaction.response.send_message(f"👥 {len(gw['participants'])} participants", ephemeral=True)

bot.run(TOKEN)
