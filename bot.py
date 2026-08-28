import discord
from discord.ext import commands
import random
import os
import json

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

PREFIX = "!"
TOKEN = os.getenv("TOKEN")

bot = commands.Bot(command_prefix=PREFIX, intents=intents)
bot.remove_command('help')

PERMS_FILE = "perms.json"
DEFAULT_PERMS = {
    "fakeid": 1,
    "snipe": 1,
    "help": 1,
    "helpall": 1,
    "perm": 1,
    "clear": 5,
    "lock": 6,
    "unlock": 6,
    "hide": 7,
    "unhide": 7,
    "warn": 5,
    "kick": 6,
    "ban": 8,
    "renew": 9,
    "set": 10,
    "change": 10
}

def load_data():
    if not os.path.exists(PERMS_FILE):
        return {"role_levels": {}, "cmd_levels": DEFAULT_PERMS}
    try:
        with open(PERMS_FILE, "r") as f:
            data = json.load(f)
            for k,v in DEFAULT_PERMS.items():
                if k not in data["cmd_levels"]:
                    data["cmd_levels"][k] = v
            return data
    except:
        return {"role_levels": {}, "cmd_levels": DEFAULT_PERMS}

def save_data(data):
    with open(PERMS_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

def get_user_level(member):
    if member.guild.owner_id == member.id:
        return 10
    max_level = 0
    for role in member.roles:
        lvl = data["role_levels"].get(str(role.id), 0)
        if lvl > max_level:
            max_level = lvl
    if max_level == 0
        return 1
    return max_level

def has_level(required_level):
    async def predicate(ctx):
        user_lvl = get_user_level(ctx.author)
        if user_lvl < required_level:
            cmd_name = ctx.command.name
            real_req = data["cmd_levels"].get(cmd_name, required_level)
            if user_lvl < real_req:
                await ctx.send(f"❌ Il te faut niveau **{real_req}** (tu es niveau {user_lvl})")
                return False
        return True
    return commands.check(predicate)

NOMS = ["Dupont", "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand", "Leroy"]
PRENOMS = ["Jean", "Pierre", "Michel", "Andre", "Philippe", "Alain", "Nicolas", "David", "Olivier", "Sebastien"]
VILLES = ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Strasbourg", "Bordeaux", "Lille", "Rennes"]
snipe_messages = {}
warns = {}

@bot.event
async def on_ready():
    print(f'Connecte en tant que {bot.user.name}')

@bot.event
async def on_message_delete(message):
    if not message.author.bot:
        snipe_messages[message.channel.id] = message

def check_perm(ctx, cmd_name):
    user_lvl = get_user_level(ctx.author)
    req = data["cmd_levels"].get(cmd_name, 1)
    if user_lvl < req:
        return False, user_lvl, req
    return True, user_lvl, req

@bot.command(name='fakeid')
async def fakeid(ctx):
    ok, ul, req = check_perm(ctx, "fakeid")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    msg = f"```\nNom : {random.choice(NOMS)}\nPrenom : {random.choice(PRENOMS)}\nVille : {random.choice(VILLES)}\nNum : +33 6 {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)}\n```"
    await ctx.send(msg)

@bot.command()
async def snipe(ctx):
    ok, ul, req = check_perm(ctx, "snipe")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    msg = snipe_messages.get(ctx.channel.id)
    if not msg: return await ctx.send("Rien à snipe.")
    embed = discord.Embed(description=msg.content, color=0xff0000)
    embed.set_author(name=str(msg.author), icon_url=msg.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='perm')
async def perm_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    lvl = get_user_level(member)
    await ctx.send(f"🔑 {member.mention} est niveau **{lvl}/10**")

@bot.command(name='set')
async def set_perms(ctx, type_: str, role: discord.Role, level: int):
    ok, ul, req = check_perm(ctx, "set")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    if type_.lower()!= "perms":
        return await ctx.send("Usage: `!set perms @role 1-10`")
    if not 1 <= level <= 10:
        return await ctx.send("Le niveau doit être entre 1 et 10")
    data["role_levels"][str(role.id)] = level
    save_data(data)
    await ctx.send(f"✅ Le rôle {role.mention} est maintenant niveau **{level}**")

@bot.command(name='change')
async def change_cmd(ctx, level: int, cmd_name: str):
    ok, ul, req = check_perm(ctx, "change")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    if not 1 <= level <= 10:
        return await ctx.send("Niveau entre 1 et 10")
    if cmd_name not in data["cmd_levels"]:
        return await ctx.send(f"Commande inconnue. Dispo : {', '.join(data['cmd_levels'].keys())}")
    data["cmd_levels"][cmd_name] = level
    save_data(data)
    await ctx.send(f"✅ La commande `{cmd_name}` passe niveau **{level}**")

@bot.command()
async def clear(ctx, amount: int = 10):
    ok, ul, req = check_perm(ctx, "clear")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    deleted = await ctx.channel.purge(limit=amount+1)
    await ctx.send(f"🧹 {len(deleted)-1} messages supprimés.", delete_after=3)

@bot.command()
async def kick(ctx, member: discord.Member, *, reason="Aucune"):
    ok, ul, req = check_perm(ctx, "kick")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    await member.kick(reason=reason)
    await ctx.send(f"✅ {member.mention} kick.")

@bot.command()
async def ban(ctx, member: discord.Member, *, reason="Aucune"):
    ok, ul, req = check_perm(ctx, "ban")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    await member.ban(reason=reason)
    await ctx.send(f"✅ {member.mention} ban.")

@bot.command()
async def warn(ctx, member: discord.Member, *, reason="Aucune"):
    ok, ul, req = check_perm(ctx, "warn")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    await ctx.send(f"⚠️ {member.mention} warn pour {reason}")

@bot.command()
async def renew(ctx):
    ok, ul, req = check_perm(ctx, "renew")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    new = await ctx.channel.clone()
    await new.edit(position=ctx.channel.position)
    await ctx.channel.delete()
    await new.send(f"Renew par {ctx.author.mention} ✅")

@bot.command()
async def lock(ctx):
    ok, ul, req = check_perm(ctx, "lock")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Verrouillé")

@bot.command()
async def unlock(ctx):
    ok, ul, req = check_perm(ctx, "unlock")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Déverrouillé")

@bot.command()
async def hide(ctx):
    ok, ul, req = check_perm(ctx, "hide")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.send("🙈 Caché")

@bot.command()
async def unhide(ctx):
    ok, ul, req = check_perm(ctx, "unhide")
    if not ok: return await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.send("👁️ Visible")

@bot.command(name='help')
async def help_cmd(ctx):
    embed = discord.Embed(title="📚 Aide", color=0x3498db)
    embed.description = "Fais `!helpall` pour voir les niveaux"
    embed.add_field(name="!fakeid!snipe!perm", value="Niveau 1", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='helpall')
async def helpall_cmd(ctx):
    embed = discord.Embed(title="🔑 Permissions 1-10", color=0x9b59b6)
    levels = {}
    for cmd, lvl in data["cmd_levels"].items():
        levels.setdefault(lvl, []).append(cmd)
    for lvl in range(1, 11):
        cmds = levels.get(lvl, [])
        if cmds:
            embed.add_field(name=f"Niveau {lvl}", value=", ".join([f"`{c}`" for c in cmds]), inline=False)
    user_lvl = get_user_level(ctx.author)
    embed.set_footer(text=f"Tu es niveau {user_lvl} |!set perms @role <niveau> |!change <niveau> <commande>")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound): return
    print(error)

if __name__ == "__main__":
    bot.run(TOKEN)
