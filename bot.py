import discord
from discord.ext import commands
import random
import datetime
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

PREFIX = "!"
TOKEN = os.getenv("TOKEN")

bot = commands.Bot(command_prefix=PREFIX, intents=intents)
bot.remove_command('help')

NOMS_DE_FAMILLE = ["Dupont", "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand", "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "David", "Bertrand", "Roux", "Morel"]
PRENOMS = ["Jean", "Pierre", "Michel", "Andre", "Philippe", "Alain", "Christian", "Daniel", "Bernard", "Patrick", "Thierry", "Christophe", "Frederic", "Didier", "Pascal", "Nicolas", "Stephane", "David", "Olivier", "Sebastien"]
VILLES_FRANCE = ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Strasbourg", "Montpellier", "Bordeaux", "Lille", "Rennes", "Reims", "Saint-Etienne", "Toulon", "Grenoble", "Dijon", "Angers", "Nimes", "Villeurbanne", "Le Mans"]

snipe_messages = {}
warns = {}

@bot.event
async def on_ready():
    print(f'Connecte en tant que {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    snipe_messages[message.channel.id] = message

@bot.command(name='fakeid')
@commands.guild_only()
async def fakeid(ctx):
    annee = random.randint(1965, 2005)
    jour = random.randint(1, 28)
    mois = random.randint(1, 12)
    msg = f"```\nNom : {random.choice(NOMS_DE_FAMILLE)}\nPrenom : {random.choice(PRENOMS)}\nDate de naissance : {jour:02d}/{mois:02d}/{annee}\nVille : {random.choice(VILLES_FRANCE)}\nNum : +33 6 {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)}\n```\n*Identite 100% fictive*"
    await ctx.send(msg)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Aucune raison"):
    await member.kick(reason=reason)
    await ctx.send(f"✅ {member.mention} a été kick pour : {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Aucune raison"):
    await member.ban(reason=reason)
    await ctx.send(f"✅ {member.mention} a été ban pour : {reason}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="Aucune raison"):
    if member.id not in warns: warns[member.id] = []
    warns[member.id].append(reason)
    await ctx.send(f"⚠️ {member.mention} a été warn pour : {reason} | Total : {len(warns[member.id])} warns")

@bot.command()
async def snipe(ctx):
    msg = snipe_messages.get(ctx.channel.id)
    if not msg:
        await ctx.send("Rien à snipe, pas de message supprimé.")
        return
    embed = discord.Embed(description=msg.content, color=0xff0000)
    embed.set_author(name=str(msg.author), icon_url=msg.author.display_avatar.url)
    embed.set_footer(text=f"Dans #{msg.channel.name}")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def renew(ctx):
    channel = ctx.channel
    new_channel = await channel.clone(reason=f"Renew par {ctx.author}")
    await new_channel.edit(position=channel.position)
    await channel.delete(reason="Renew")
    await new_channel.send(f"Salon renew par {ctx.author.mention} ✅")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Salon verrouillé, plus personne ne peut parler.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Salon déverrouillé.")

@bot.command(name='help')
async def help_cmd(ctx):
    embed = discord.Embed(title="📚 Aide", color=0x3498db)
    embed.add_field(name="!fakeid", value="Génère une fausse identité", inline=False)
    embed.add_field(name="!kick @user [raison]", value="Kick un membre", inline=False)
    embed.add_field(name="!ban @user [raison]", value="Ban un membre", inline=False)
    embed.add_field(name="!warn @user [raison]", value="Warn un membre", inline=False)
    embed.add_field(name="!snipe", value="Affiche le dernier message supprimé", inline=False)
    embed.add_field(name="!renew", value="Recrée le salon (clean)", inline=False)
    embed.add_field(name="!lock /!unlock", value="Verrouille / déverrouille le salon", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas la perm.")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        print(error)

if __name__ == "__main__":
    bot.run(TOKEN)
