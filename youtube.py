import discord
from discord import app_commands
from discord.ext import commands, tasks
import feedparser

ADMIN_ROLE_IDS = [
    1562121971259539476,
]


class YouTubeConfigModal(discord.ui.Modal, title="⚙️ Configuration YouTube"):
    yt_channel_id = discord.ui.TextInput(
        label="ID de la chaîne YouTube",
        placeholder="ex: UCxxxxxxxxx...",
        required=True,
        min_length=10,
    )

    def __init__(self, target_channel: discord.TextChannel, youtube_cog):
        super().__init__()
        self.target_channel = target_channel
        self.youtube_cog = youtube_cog

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        channel_id_yt = self.yt_channel_id.value.strip()

        if not hasattr(self.youtube_cog.bot, "yt_config"):
            self.youtube_cog.bot.yt_config = {}

        self.youtube_cog.bot.yt_config[guild_id] = {
            "channel_id": self.target_channel.id,
            "yt_username": channel_id_yt,
        }

        # Récupération immédiate pour ne pas re-notifier une ancienne vidéo
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id_yt}"
        feed = feedparser.parse(rss_url)
        if feed.entries:
            self.youtube_cog.derniers_liens[channel_id_yt] = feed.entries[0].link

        embed = discord.Embed(
            title="✅ Configuration Enregistrée !",
            description=(
                f"**Salon d'annonce :** {self.target_channel.mention}\n"
                f"**ID Chaîne YouTube :** `{channel_id_yt}`\n\n"
                f"🔔 Les nouvelles vidéos seront annoncées ici automatiquement !"
            ),
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class YouTubeControlView(discord.ui.View):
    def __init__(self, youtube_cog):
        super().__init__(timeout=None)
        self.youtube_cog = youtube_cog

    @discord.ui.button(
        label="Configurer / Modifier",
        style=discord.ButtonStyle.success,
        emoji="⚙️",
        custom_id="yt_cfg_btn",
    )
    async def configurer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.youtube_cog.est_admin(interaction):
            await interaction.response.send_message("❌ Action réservée aux admins.", ephemeral=True)
            return

        # Demander le salon avant d'ouvrir le Modal
        select_channel = discord.ui.ChannelSelect(
            placeholder="Sélectionne le salon d'annonce...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
        )

        async def channel_callback(inter: discord.Interaction):
            target_chan = select_channel.values[0]
            await inter.response.send_modal(YouTubeConfigModal(target_chan, self.youtube_cog))

        select_channel.callback = channel_callback

        view_channel = discord.ui.View(timeout=60)
        view_channel.add_item(select_channel)

        await interaction.response.send_message(
            "📌 **Étape 1 :** Choisis le salon où envoyer les notifications :",
            view=view_channel,
            ephemeral=False,
        )

    @discord.ui.button(
        label="Vérifier Statut",
        style=discord.ButtonStyle.primary,
        emoji="🔍",
        custom_id="yt_status_btn",
    )
    async def statut(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        config = getattr(self.youtube_cog.bot, "yt_config", {}).get(guild_id)

        if not config:
            await interaction.response.send_message(
                "❌ Aucune configuration YouTube active sur ce serveur.", ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(config["channel_id"])
        embed = discord.Embed(
            title="📊 Statut du Module YouTube",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Salon", value=channel.mention if channel else "Inconnu", inline=True)
        embed.add_field(name="ID Chaîne YT", value=f"`{config['yt_username']}`", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Supprimer",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="yt_delete_btn",
    )
    async def supprimer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.youtube_cog.est_admin(interaction):
            await interaction.response.send_message("❌ Action réservée aux admins.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        if hasattr(self.youtube_cog.bot, "yt_config") and guild_id in self.youtube_cog.bot.yt_config:
            del self.youtube_cog.bot.yt_config[guild_id]
            await interaction.response.send_message("✅ Configuration YouTube supprimée !", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Aucune configuration à supprimer.", ephemeral=True)


class YouTube(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.derniers_liens = {}
        self.verifier_youtube.start()

    def cog_unload(self):
        self.verifier_youtube.cancel()

    def est_admin(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        return any(role.id in ADMIN_ROLE_IDS for role in interaction.user.roles)

    @tasks.loop(minutes=10)
    async def verifier_youtube(self):
        if not hasattr(self.bot, "yt_config") or not self.bot.yt_config:
            return

        for guild_id, config in list(self.bot.yt_config.items()):
            channel_id = config["channel_id"]
            yt_username = config["yt_username"]

            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={yt_username}"
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                continue

            derniere_video = feed.entries[0]
            video_url = derniere_video.link
            video_title = derniere_video.title
            video_author = derniere_video.author

            if yt_username not in self.derniers_liens:
                self.derniers_liens[yt_username] = video_url
                continue

            if self.derniers_liens[yt_username] != video_url:
                self.derniers_liens[yt_username] = video_url
                guild = self.bot.get_guild(guild_id)
                if guild:
                    salon = guild.get_channel(channel_id)
                    if salon:
                        embed = discord.Embed(
                            title="🎬 Nouvelle vidéo disponible !",
                            description=f"**[{video_title}]({video_url})**",
                            color=discord.Color.red(),
                        )
                        embed.set_author(name=video_author)
                        embed.set_footer(text="Abonnez-vous et activez la cloche !")
                        await salon.send(
                            f"📢 Hey @everyone ! **{video_author}** vient de sortir une nouvelle vidéo !",
                            embed=embed,
                        )

    @verifier_youtube.before_loop
    async def before_verifier_youtube(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="youtube", description="Panneau interactif de gestion YouTube")
    async def youtube_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📺 GESTION DE NOTIFICATIONS YOUTUBE",
            description=(
                "Bienvenue dans le panneau d'administration YouTube !\n\n"
                "• Cliquez sur **Configurer / Modifier** pour associer un salon et une chaîne.\n"
                "• Cliquez sur **Vérifier Statut** pour voir la configuration actuelle.\n"
                "• Cliquez sur **Supprimer** pour retirer l'annonceur automatique."
            ),
            color=discord.Color.red(),
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1384/1384060.png")
        await interaction.response.send_message(
            embed=embed, view=YouTubeControlView(self)
        )

async def setup(bot):
    await bot.add_cog(YouTube(bot))