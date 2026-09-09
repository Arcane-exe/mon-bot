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
def home(): return "4Protect V2 + Snoway - Prefix + ON"
def run_web(): app.run(host="0.0.0.0", port=10000)
threading.Thread(target=run_web, daemon=True).start()

DB_FILE = "db.json"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({
            "whitelist":[], "antilink":{}, "antispam":{}, "antibot":{},
            "antichannel":{}, "antirole":{}, "antiban":{}, "antikick":{},
            "antiraid":{}, "welcome":{}, "logs":{}, "autorole":{}, "warns":{}
        }, f, indent=4)

def get_db():
    with open(DB_FILE, "r") as f: return json.load(f)
def save_db(d):
    with open(DB_FILE, "w") as f: json.dump(d, f, indent=4)
def is_wl(uid):
    try: return uid in get_db()["whitelist"]
    except: return False

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="+", intents=intents, help_command=None)

join_cache = defaultdict(list)
spam_cache = defaultdict(list)
snipe_cache = {}

def be(embed, interaction=None, ctx=None):
    embed.color = 0x2B2D31
    embed.timestamp = datetime.now()
    if interaction:
        embed.set_footer(text=f"Demandé par {interaction.user}", icon_url=interaction.user.display_avatar.url)
    elif ctx:
        embed.set_footer(text=f"Demandé par {ctx.author}", icon_url=ctx.author.display_avatar.url)
    return embed

@bot.event
async def on_ready():
    print(f"Connecté: {bot.user} | Prefix: +")
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
            discord.SelectOption(label="Protect", emoji="🛡️", description="antilink, antibot, antiraid..."),
            discord.SelectOption(label="Modération", emoji="🔨", description="ban, kick, timeout, clear..."),
            discord.SelectOption(label="Gestion", emoji="⚙️", description="logs, welcome, autorole, whitelist"),
            discord.SelectOption(label="Utile", emoji="💎", description="ping, avatar, serverinfo, snipe"),
        ])
    async def callback(self, interaction: discord.Interaction):
        if self.values[0]=="Protect":
            e = discord.Embed(title="🛡️ Protect", description="```+antilink on/off\n+antispam on/off\n+antibot on/off\n+antichannel on/off\n+antirole on/off\n+antiban on/off\n+antikick on/off\n+antiraid on/off```", color=0x2B2D31)
        elif self.values[0]=="Modération":
            e = discord.Embed(title="🔨 Modération", description="```+ban @membre raison\n+kick @membre\n+timeout @membre 5\n+unban ID\n+clear 50\n+lock\n+unlock\n+warn @membre raison```", color=0x2B2D31)
        elif self.values[0]=="Gestion":
            e = discord.Embed(title="⚙️ Gestion", description="```+whitelist add @membre\n+whitelist remove @membre\n+whitelist list\n+setlogs #salon\n+setwelcome #salon\n+setautorole @role\n+panel```", color=0x2B2D31)
        else:
            e = discord.Embed(title="💎 Utile", description="```+ping\n+avatar @membre\n+serverinfo\n+snipe\n+help```", color=0x2B2D31)
        await interaction.response.edit_message(embed=be(e, interaction))
class HelpView(discord.ui.View):
    def __init__(self): super().__init__(timeout=120); self.add_item(HelpSelect())
class ProtectView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="AntiLink", style=discord.ButtonStyle.gray, emoji="🔗")
    async def al(self, interaction, button):
        db=get_db(); gid=str(interaction.guild.id); en=not db["antilink"].get(gid,{}).get("enabled",False)
        db.setdefault("antilink", {}).setdefault(gid, {})["enabled"]=en; save_db(db)
        await interaction.response.send_message(f"AntiLink {'ON' if en else 'OFF'}", ephemeral=True)
    @discord.ui.button(label="AntiBot", style=discord.ButtonStyle.gray, emoji="🤖")
    async def ab(self, interaction, button):
        db=get_db(); gid=str(interaction.guild.id); en=not db["antibot"].get(gid,{}).get("enabled",False)
        db.setdefault("antibot", {}).setdefault(gid, {})["enabled"]=en; save_db(db)
        await interaction.response.send_message(f"AntiBot {'ON' if en else 'OFF'}", ephemeral=True)
    @discord.ui.button(label="Activer Tout", style=discord.ButtonStyle.red, emoji="🚨")
    async def all_on(self, interaction, button):
        db=get_db(); gid=str(interaction.guild.id)
        for k in ["antilink","antispam","antibot","antichannel","antirole","antiban","antikick","antiraid"]:
            db.setdefault(k, {}).setdefault(gid, {})["enabled"]=True
        save_db(db)
        await interaction.response.send_message("✅ Toutes les protections ON", ephemeral=True)

@bot.tree.command(name="help", description="Panel d'aide")
async def help_slash(interaction: discord.Interaction):
    e = discord.Embed(title="4Protect + Snoway - Panel", description="> **Prefix: `+`**\n\n`🛡️` Protect\n`🔨` Modération\n`⚙️` Gestion\n`💎` Utile", color=0x2B2D31)
    e.set_thumbnail(url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=be(e, interaction), view=HelpView())
@bot.tree.command(name="panel", description="Panel protection")
async def panel_slash(interaction: discord.Interaction):
    db=get_db(); gid=str(interaction.guild.id)
    desc = f"**AntiLink:** {'🟢' if db['antilink'].get(gid,{}).get('enabled') else '🔴'}\n**AntiSpam:** {'🟢' if db['antispam'].get(gid,{}).get('enabled') else '🔴'}\n**AntiBot:** {'🟢' if db['antibot'].get(gid,{}).get('enabled') else '🔴'}\n**AntiChannel:** {'🟢' if db['antichannel'].get(gid,{}).get('enabled') else '🔴'}\n**AntiRole:** {'🟢' if db['antirole'].get(gid,{}).get('enabled') else '🔴'}\n**AntiBan:** {'🟢' if db['antiban'].get(gid,{}).get('enabled') else '🔴'}\n**AntiRaid:** {'🟢' if db['antiraid'].get(gid,{}).get('enabled') else '🔴'}"
    e = discord.Embed(title="🛡️ Control Panel", description=desc, color=0x2B2D31)
    await interaction.response.send_message(embed=be(e, interaction), view=ProtectView())

def toggle_prefix(name, key):
    @bot.command(name=name)
    @commands.has_permissions(administrator=True)
    async def cmd(ctx, status: str = None):
        if not status or status.lower() not in ["on","off"]:
            return await ctx.send(f"Usage: `+{name} on/off`")
        db=get_db(); gid=str(ctx.guild.id)
        db.setdefault(key, {}).setdefault(gid, {})["enabled"]=(status.lower()=="on")
        save_db(db)
        await ctx.send(embed=be(discord.Embed(title=f"🛡️ {name}", description=f"**{status.upper()}**"), ctx=ctx))
    return cmd

for n,k in [("antilink","antilink"),("antispam","antispam"),("antibot","antibot"),("antichannel","antichannel"),("antirole","antirole"),("antiban","antiban"),("antikick","antikick"),("antiraid","antiraid")]:
    toggle_prefix(n,k)

@bot.command(name="help")
async def help_p(ctx):
    e = discord.Embed(title="4Protect + Snoway - Panel", description="> **Prefix: `+`**\n\n`🛡️` Protect: `+antilink on/off` etc\n`🔨` Modération: `+ban`, `+kick`, `+clear`\n`⚙️` Gestion: `+whitelist`, `+setlogs`\n`💎` Utile: `+ping`, `+avatar`, `+snipe`", color=0x2B2D31)
    e.set_thumbnail(url=bot.user.display_avatar.url)
    await ctx.send(embed=be(e, ctx=ctx), view=HelpView())

@bot.command(name="panel")
@commands.has_permissions(administrator=True)
async def panel_p(ctx):
    db=get_db(); gid=str(ctx.guild.id)
    desc = f"**AntiLink:** {'🟢' if db['antilink'].get(gid,{}).get('enabled') else '🔴'}\n**AntiSpam:** {'🟢' if db['antispam'].get(gid,{}).get('enabled') else '🔴'}\n**AntiBot:** {'🟢' if db['antibot'].get(gid,{}).get('enabled') else '🔴'}\n**AntiChannel:** {'🟢' if db['antichannel'].get(gid,{}).get('enabled') else '🔴'}\n**AntiRole:** {'🟢' if db['antirole'].get(gid,{}).get('enabled') else '🔴'}\n**AntiBan:** {'🟢' if db['antiban'].get(gid,{}).get('enabled') else '🔴'}\n**AntiRaid:** {'🟢' if db['antiraid'].get(gid,{}).get('enabled') else '🔴'}"
    e = discord.Embed(title="🛡️ Control Panel", description=desc, color=0x2B2D31)
    await ctx.send(embed=be(e, ctx=ctx), view=ProtectView())

@bot.command(name="whitelist")
@commands.has_permissions(administrator=True)
async def whitelist_p(ctx, action: str = None, member: discord.Member = None):
    db=get_db()
    if action=="add" and member:
        if member.id not in db["whitelist"]: db["whitelist"].append(member.id)
        save_db(db); await ctx.send(embed=be(discord.Embed(description=f"✅ {member.mention} whitelist"), ctx=ctx))
    elif action=="remove" and member:
        if member.id in db["whitelist"]: db["whitelist"].remove(member.id)
        save_db(db); await ctx.send(embed=be(discord.Embed(description=f"❌ {member.mention} retiré"), ctx=ctx))
    else:
        lst="\n".join([f"<@{uid}> - {uid}" for uid in db["whitelist"]]) or "Vide"
        await ctx.send(embed=be(discord.Embed(title="Whitelist", description=lst), ctx=ctx))

@bot.command(name="setlogs")
@commands.has_permissions(administrator=True)
async def setlogs_p(ctx, salon: discord.TextChannel):
    db=get_db(); db["logs"][str(ctx.guild.id)]=salon.id; save_db(db)
    await ctx.send(embed=be(discord.Embed(description=f"Logs: {salon.mention}"), ctx=ctx))

@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def setwelcome_p(ctx, salon: discord.TextChannel):
    db=get_db(); db["welcome"][str(ctx.guild.id)]=salon.id; save_db(db)
    await ctx.send(embed=be(discord.Embed(description=f"Welcome: {salon.mention}"), ctx=ctx))

@bot.command(name="setautorole")
@commands.has_permissions(administrator=True)
async def setautorole_p(ctx, role: discord.Role):
    db=get_db(); db["autorole"][str(ctx.guild.id)]=role.id; save_db(db)
    await ctx.send(embed=be(discord.Embed(description=f"Autorole: {role.mention}"), ctx=ctx))

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_p(ctx, member: discord.Member = None, *, reason="Aucune"):
    if not member: return await ctx.send("Usage: `+ban @membre raison`")
    if is_wl(member.id): return await ctx.send("Whitelist")
    await member.ban(reason=reason); await ctx.send(embed=be(discord.Embed(title="🔨 Ban", description=f"{member.mention} banni: {reason}"), ctx=ctx))

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_p(ctx, member: discord.Member = None, *, reason="Aucune"):
    if not member: return await ctx.send("Usage: `+kick @membre`")
    await member.kick(reason=reason); await ctx.send(embed=be(discord.Embed(description=f"{member.mention} kick"), ctx=ctx))

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout_p(ctx, member: discord.Member = None, minutes: int = 5, *, reason="Spam"):
    if not member: return await ctx.send("Usage: `+timeout @membre 5`")
    await member.timeout(timedelta(minutes=minutes), reason=reason); await ctx.send(embed=be(discord.Embed(description=f"{member.mention} mute {minutes}min"), ctx=ctx))

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear_p(ctx, nombre: int = 10):
    d = await ctx.channel.purge(limit=nombre)
    await ctx.send(f"✅ {len(d)} messages supprimés", delete_after=5)

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock_p(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(embed=be(discord.Embed(title="🔒 Vérouillé"), ctx=ctx))

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock_p(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(embed=be(discord.Embed(title="🔓 Déverrouillé"), ctx=ctx))

@bot.command(name="avatar")
async def avatar_p(ctx, member: discord.Member = None):
    m=member or ctx.author
    e=discord.Embed(title=f"Avatar {m.name}", color=0x2B2D31); e.set_image(url=m.display_avatar.url)
    await ctx.send(embed=be(e, ctx=ctx))

@bot.command(name="snipe")
async def snipe_p(ctx):
    data=snipe_cache.get(ctx.channel.id)
    if not data: return await ctx.send("Rien à snipe")
    e=discord.Embed(title="Snipe", description=data["content"], color=0x2B2D31); e.set_author(name=str(data["author"]), icon_url=data["author"].display_avatar.url)
    await ctx.send(embed=e)

@bot.command(name="serverinfo")
async def serverinfo_p(ctx):
    g=ctx.guild; e=discord.Embed(title=g.name, description=f"Owner: <@{g.owner_id}>\nMembres: {g.member_count}\nBoosts: {g.premium_subscription_count}", color=0x2B2D31)
    e.set_thumbnail(url=g.icon.url if g.icon else None)
    await ctx.send(embed=be(e, ctx=ctx))

@bot.command(name="ping")
async def ping_p(ctx):
    await ctx.send(embed=be(discord.Embed(description=f"🏓 {round(bot.latency*1000)}ms"), ctx=ctx))

@bot.command(name="warn")
@commands.has_permissions(moderate_members=True)
async def warn_p(ctx, member: discord.Member = None, *, reason="Aucune"):
    if not member: return await ctx.send("Usage: `+warn @membre raison`")
    try: await member.send(f"⚠️ Warn sur {ctx.guild.name}: {reason}")
    except: pass
    await ctx.send(embed=be(discord.Embed(description=f"⚠️ {member.mention} warn: {reason}"), ctx=ctx))

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban_p(ctx, user_id: str = None):
    if not user_id: return await ctx.send("Usage: `+unban ID`")
    try:
        user = await bot.fetch_user(int(user_id))
        await ctx.guild.unban(user); await ctx.send(f"🔓 {user} débanni")
    except: await ctx.send("❌ Introuvable")

bot.run(TOKEN)
