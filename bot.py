import discord
from discord.ext import commands
import random
import datetime
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

PREFIX = "!"
TOKEN = os.getenv("TOKEN")

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

NOMS_DE_FAMILLE = ["Dupont", "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand", "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "David", "Bertrand", "Roux", "Morel"]
PRENOMS = ["Jean", "Pierre", "Michel", "Andre", "Philippe", "Alain", "Christian", "Daniel", "Bernard", "Patrick", "Thierry", "Christophe", "Frederic", "Didier", "Pascal", "Nicolas", "Stephane", "David", "Olivier", "Sebastien"]
VILLES_FRANCE = ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Strasbourg", "Montpellier", "Bordeaux", "Lille", "Rennes", "Reims", "Saint-Etienne", "Toulon", "Grenoble", "Dijon", "Angers", "Nimes", "Villeurbanne", "Le Mans"]

@bot.event
async def on_ready():
    print(f'Connecte en tant que {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name=f"avec {PREFIX}help"))

@bot.command(name='fakeid')
@commands.guild_only()
async def fakeid(ctx):
    annee_actuelle = datetime.datetime.now().year
    annee_naissance = random.randint(annee_actuelle - 60, annee_actuelle - 18)
    jour = random.randint(1, 28)
    mois = random.randint(1, 12)
    
    embed = discord.Embed(title="🪪 Fausse identité", color=0x8e44ad)
    embed.add_field(name="Nom", value=random.choice(NOMS_DE_FAMILLE), inline=True)
    embed.add_field(name="Prénom", value=random.choice(PRENOMS), inline=True)
    embed.add_field(name="Naissance", value=f"{jour:02d}/{mois:02d}/{annee_naissance}", inline=False)
    embed.add_field(name="Ville", value=random.choice(VILLES_FRANCE), inline=True)
    embed.add_field(name="Num", value=f"+33 6 {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)}", inline=True)
    embed.set_footer(text="Identité 100% fictive - pour le fun uniquement")
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Erreur: {error}")

@bot.command(name='help')
async def help_custom(ctx):
    embed = discord.Embed(title="📚 Aide du bot", color=0x3498db)
    embed.add_field(name="!fakeid", value="Génère une fausse identité aléatoire", inline=False)
    embed.add_field(name="!help", value="Affiche ce message", inline=False)
    await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
