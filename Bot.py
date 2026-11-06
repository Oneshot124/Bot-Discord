import os
import asyncio
import discord
from discord.ext import commands
from app import keep_alive

# Intents nécessaires pour le bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 1. Chargement de tous les fichiers .py (Cogs)
        for filename in os.listdir("."):
            if filename.endswith(".py") and filename not in [
                "Bot.py",
                "app.py",
                "database.py",
                "s'abonner.py",
            ]:
                cog_name = filename[:-3]
                try:
                    await self.load_extension(cog_name)
                    print(f"✅ Extension chargée : {cog_name}")
                except Exception as e:
                    print(f"❌ Erreur lors du chargement de {cog_name} : {e}")

        # 2. Synchronisation instantanée des commandes sur tes serveurs
        # (Copie les commandes directement sur chaque serveur où se trouve le bot)
        for guild in self.guilds:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"⚡ Commandes synchronisées instantanément pour le serveur : {guild.name}")

    async def on_ready(self):
        print(f"🤖 Bot connecté en tant que {self.user} (ID: {self.user.id})")

bot = MyBot()

# Démarre le serveur Flask web pour UptimeRobot
keep_alive()

# Lancement du bot avec le Token d'environnement
token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ Erreur : Le token DISCORD_TOKEN est introuvable.")
