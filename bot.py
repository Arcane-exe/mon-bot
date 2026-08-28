
import discord
from discord.ext import commands
import random
import datetime

intents = discord.Intents.default()
intents.members = True            
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

NOMS_DE_FAMILLE = ["Dupont", "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand", "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "David", "Bertrand", "Roux", "Morel"]
PRENOMS = ["Jean", "Pierre", "Michel", "André", "Philippe", "Alain", "Christian", "Daniel", "Bernard", "Patrick", "Thierry", "Christophe", "Frédéric", "Didier", "Pascal", "Nicolas", "Stéphane", "David", "Olivier", "Sébastien"]
VILLES_FRANCE = ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Strasbourg", "Montpellier", "Bordeaux", "Lille", "Rennes", "Reims", "Saint-Étienne", "Toulon", "Grenoble", "Dijon", "Angers", "Nîmes", "Villeurbanne", "Le Mans"]

@bot.event
async def on_ready():
    """Se déclenche lorsque le bot est prêt et connecté à Discord."""
    print(f'Connecté en tant que {bot.user.name}')
    print(f'ID du bot : {bot.user.id}')
    print('------')
    await bot.change_presence(activity=discord.Game(name=f"avec {PREFIX}help"))

@bot.command(name='dox', help='Affiche de fausses informations sur un utilisateur.')
@commands.guild_only()
async def dox(ctx, member: discord.Member = None):
    """Génère de fausses informations sur un utilisateur mentionné."""
    if member is None:
        member = ctx.author 

    annee_actuelle = datetime.datetime.now().year
    annee_naissance = random.randint(annee_actuelle - 60, annee_actuelle - 18) 
    jour = random.randint(1, 28)
    mois = random.randint(1, 12)
    date_naissance = f"{jour:02d}/{mois:02d}/{annee_naissance}" 

    numero_tel = f"+3306{random.randint(10000000, 99999999)}" 

    message_dox = f"""
    ```
    Nom : {random.choice(NOMS_DE_FAMILLE)}
    Prénom : {random.choice(PRENOMS)}
    Date de naissance : {date_naissance}
    Ville : {random.choice(VILLES_FRANCE)}
    Num : {numero_tel}
    ```
    En vrai Force à toi bg
    """

    await ctx.send(message_dox)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"Tu n'as pas les permissions nécessaires pour utiliser cette commande.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Cette commande n'existe pas.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Il manque un argument pour cette commande. Utilise `{PREFIX}help {ctx.command.name}` pour plus d'informations.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Un argument n'est pas valide. Vérifie le type d'argument attendu.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("Je n'ai pas les permissions nécessaires pour exécuter cette commande. Demande à un administrateur de me donner les bonnes permissions.")
    else:
        print(f"Une erreur est survenue : {error}")
        await ctx.send("Une erreur interne est survenue lors de l'exécution de la commande.")

if __name__ == "__main__":
    if TOKEN == "TOKEN"
    else:
        bot.run(TOKEN)
 
