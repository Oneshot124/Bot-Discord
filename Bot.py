import os
from pathlib import Path
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import database as db

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("❌ Le token Discord est introuvable dans le fichier .env ou les variables d'environnement !")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MonBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!!", intents=intents)

    async def setup_hook(self):
        await db.init_db()

        # Chargement direct des fichiers .py situés à la racine
        for filename in os.listdir("."):
            if filename.endswith(".py") and filename not in ["Bot.py", "app.py", "database.py", "s'abonner.py"]:
                cog_name = filename[:-3]
                await self.load_extension(cog_name)

        await self.tree.sync()
        print("✅ Base de données et extensions chargées avec succès !")

    async def on_ready(self):
        print(f"🤖 Bot connecté sous le nom : {self.user.name}")

bot = MonBot()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        heures, minutes = int(error.retry_after // 3600), int((error.retry_after % 3600) // 60)
        await interaction.response.send_message(f"⏳ Reviens dans **{heures}h et {minutes}min** !", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Tu n'as pas la permission d'exécuter cette commande.", ephemeral=True)
    else:
        print(f"Erreur d'exécution : {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Une erreur inattendue est survenue.", ephemeral=True)

if __name__ == "__main__":
    bot.run(token)