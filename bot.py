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
    "snipe": 1, "help": 1, "helpall": 1, "perm": 1,
    "clear": 5, "lock": 6, "unlock": 6, "hide": 7, "unhide": 7,
    "warn": 5, "kick": 6, "ban": 8, "renew": 9, "set": 10, "change": 10
}

def load_data():
    if not os.path.exists(PERMS_FILE):
        return {"role_levels": {}, "cmd_levels": DEFAULT_PERMS}
    with open(PERMS_FILE, "r") as f:
        return json.load(f)

def save_data(d):
    with open(PERMS_FILE, "w") as f:
        json.dump(d, f, indent=4)

data = load_data()

def get_user_level(member):
    # Si personne n'a encore de perms, l'admin du serveur est niveau 10
    if len(data["role_levels"]) == 0:
        if member.guild_permissions.administrator or member.guild.owner_id == member.id:
            return 10
    if member.guild.owner_id == member.id:
        return 10
    max_lvl = 0
    for role in member.roles:
        lvl = data["role_levels"].get(str(role.id), 0)
        if lvl > max_lvl:
            max_lvl = lvl
    return max_lvl if max_lvl != 0 else 1

def check_perm(ctx, cmd):
    ul = get_user_level(ctx.author)
    req = data["cmd_levels"].get(cmd, 1)
    if ul < req:
        return False, ul, req
    return True, ul, req

snipe_messages = {}

@bot.event
async def on_ready():
    print(f"Connecte en tant que {bot.user.name}")

@bot.event
async def on_message_delete(message):
    if not message.author.bot:
        snipe_messages[message.channel.id] = message

@bot.command(name="perm")
async def perm_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    lvl = get_user_level(member)
    await ctx.send(f"🔑 {member.mention} niveau {lvl}/10")

@bot.command(name="set")
async def set_perms(ctx, type_name, role: discord.Role, level: int):
    ok, ul, req = check_perm(ctx, "set")
    if not ok:
        await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
        return
    if type_name!= "perms":
        await ctx.send("Usage:!set perms @role 1-10")
        return
    data["role_levels"][str(role.id)] = level
    save_data(data)
    await ctx.send(f"✅ {role.mention} niveau {level}")

@bot.command(name="change")
async def change_cmd(ctx, level: int, cmd_name: str):
    ok, ul, req = check_perm(ctx, "change")
    if not ok:
        await ctx.send(f"❌ Niveau {req} requis (tu es {ul})")
        return
    data["cmd_levels"][cmd_name] = level
    save_data(data)
    await ctx.send(f"✅ {cmd_name} passe niveau {level}")

@bot.command()
async def clear(ctx, amount: int = 10):
    ok, ul, req = check_perm(ctx, "clear")
    if not ok:
        await ctx.send(f"❌ Niveau {req} requis")
        return
    deleted = await ctx.channel.purge(limit=amount+1)
    await ctx.send(f"🧹 {len(deleted)-1} suppr", delete_after=3)

@bot.command()
async def kick(ctx, member: discord.Member):
    ok, ul, req = check_perm(ctx, "kick")
    if not ok:
        await ctx.send(f"❌ Niveau {req} requis")
        return
    await member.kick()
    await ctx.send(f"✅ {member.mention} kick")

@bot.command()
async def ban(ctx, member: discord.Member):
    ok, ul, req = check_perm(ctx, "ban")
    if not ok:
        await ctx.send(f"❌ Niveau {req} requis")
        return
    await member.ban()
    await ctx.send(f"✅ {member.mention} ban")

@bot.command()
async def warn(ctx, member: discord.Member):
    ok, ul, req = check_perm(ctx, "warn")
    if not ok:
        await ctx.send(f"❌ Niveau {req} requis")
        return
    await ctx.send(f"⚠️ {member.mention} warn")

@bot.command()
async def snipe(ctx):
    msg = snipe_messages.get(ctx.channel.id)
    if not msg:
        await ctx.send("Rien a snipe")
        return
    await ctx.send(msg.content)

@bot.command()
async def renew(ctx):
    ok, ul, req = check_perm(ctx, "renew")
    if not ok:
        await ctx.send(f"❌ Niveau {req} requis")
        return
    new = await ctx.channel.clone()
    await new.edit(position=ctx.channel.position)
    await ctx.channel.delete()
    await new.send(f"Renew par {ctx.author.mention}")

@bot.command()
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Verrouille")

@bot.command()
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Deverrouille")

@bot.command()
async def hide(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.send("🙈 Cache")

@bot.command()
async def unhide(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.send("👁️ Visible")

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(title="📚 Bot Arcane - Aide", color=0x9b59b6)
    embed.add_field(name="🎭 Fun", value="`!snipe`", inline=False)
    embed.add_field(name="🛡️ Modo", value="`!clear` `!kick` `!ban` `!warn` `!renew`", inline=False)
    embed.add_field(name="🔒 Salon", value="`!lock` `!unlock` `!hide` `!unhide`", inline=False)
    embed.add_field(name="🔑 Perms", value="`!perm` `!set perms @role 1-10` `!change <niv> <cmd>` `!helpall`", inline=False)
    embed.set_footer(text="Fais !helpall pour voir les niveaux 1-10")
    await ctx.send(embed=embed)

@bot.command(name="helpall")
async def helpall_cmd(ctx):
    embed = discord.Embed(title="Permissions 1-10", color=0x9b59b6)
    levels = {}
    for cmd, lvl in data["cmd_levels"].items():
        levels.setdefault(lvl, []).append(cmd)
    for lvl in range(1, 11):
        if lvl in levels:
            embed.add_field(name=f"Niveau {lvl}", value=", ".join(levels[lvl]), inline=False)
    await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
