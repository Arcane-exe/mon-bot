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
    print(f'ID du bot : {bot.user.id}')
    print('------')
    await bot.change_presence(activity=discord.Game(name=f"avec {PREFIX}help"))

@bot.command(name='fakeid', help='Genere de fausses informations pour le fun.')
@commands.guild_only()
async def fakeid(ctx):
    annee_actuelle = datetime.datetime.now().year
    annee_naissance = random.randint(annee_actuelle - 60, annee_actuelle - 18)
    jour = random.randint(1, 28)
    mois = random.randint(1, 12)
    date_naissance = f"{jour:02d}/{mois:02d}/{annee_naissance}"
    numero_tel = f"+3306{random.randint(10000000, 99999999)}"
    message = f"```\nNom : {random.choice(NOMS_DE_FAMILLE)}\nPrenom : {random.choice(PRENOMS)}\nDate de naissance : {date_naissance}\nVille : {random.choice(VILLES_FRANCE)}\nNum : {numero_tel}\n```\n**En vrai Force à toi bg**"
    await ctx.send(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Tu n'as pas les permissions necessaires.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Cette commande n'existe pas.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Il manque un argument. Utilise {PREFIX}help {ctx.command.name}")
    else:
        print(f"Une erreur est survenue : {error}")
        await ctx.send("Une erreur interne est survenue.")

if __name__ == "__main__":
    if not TOKEN:
        print("Erreur: TOKEN non defini dans Render")
    else:
        bot.run(TOKEN)
