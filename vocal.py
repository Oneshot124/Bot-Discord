import discord
from discord.ext import commands
from discord import app_commands


class VocalControlModal(discord.ui.Modal, title="Modifier le salon vocal"):
    nom = discord.ui.TextInput(
        label="Nouveau nom du salon",
        placeholder="Ex: Salon de MonPseudo",
        max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
            await channel.edit(name=str(self.nom))
            await interaction.response.send_message(
                f"✅ Salon renommé en **{self.nom}** !", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Vous n'êtes pas dans un salon vocal géré.", ephemeral=True
            )


class VocalControlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Renommer", style=discord.ButtonStyle.primary, emoji="✏️"
    )
    async def rename_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(VocalControlModal())

    @discord.ui.button(
        label="Verrouiller/Ouvrir",
        style=discord.ButtonStyle.secondary,
        emoji="🔒",
    )
    async def lock_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
            overwrite = channel.overwrites_for(interaction.guild.default_role)

            if overwrite.connect is False:
                overwrite.connect = True
                msg = "🔓 Le salon est de nouveau **ouvert** au public."
            else:
                overwrite.connect = False
                msg = "🔒 Le salon est maintenant **verrouillé**."

            await channel.set_permissions(
                interaction.guild.default_role, overwrite=overwrite
            )
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Vous n'êtes pas dans votre salon vocal.", ephemeral=True
            )


class TempVocal(commands.Cog):
    # Nom exact du salon vocal sur lequel cliquer pour créer un vocal
    TRIGGER_CHANNEL_NAME = "➕ ┃ Créer un vocal"

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # 1. Si l'utilisateur rejoint le salon "Créer un vocal"
        if after.channel and after.channel.name == self.TRIGGER_CHANNEL_NAME:
            guild = member.guild
            category = after.channel.category

            channel_name = f"🔊 ┃ {member.display_name}"
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=True),
                member: discord.PermissionOverwrite(
                    manage_channels=True,
                    move_members=True,
                    mute_members=True,
                    deafen_members=True,
                ),
            }

            # Création du salon vocal personnel
            new_channel = await guild.create_voice_channel(
                name=channel_name, category=category, overwrites=overwrites
            )

            # Déplacement automatique du membre dedans
            await member.move_to(new_channel)

            # Envoi du panneau de contrôle interactif dans le chat du vocal
            view = VocalControlView()
            try:
                await new_channel.send(
                    f"🎛️ **Panneau de contrôle de ton salon, {member.mention}**\nUtilise les boutons ci-dessous pour gérer ton espace :",
                    view=view,
                )
            except Exception:
                pass

        # 2. Si un salon temporaire devient vide, on le supprime automatiquement
        if before.channel and before.channel != after.channel:
            if (
                before.channel.name.startswith("🔊 ┃")
                and len(before.channel.members) == 0
            ):
                try:
                    await before.channel.delete()
                except Exception:
                    pass


async def setup(bot):
    await bot.add_cog(TempVocal(bot))
