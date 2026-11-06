import discord
from discord.ext import commands
from discord import app_commands

channel_owners = {}

class VocalControlModal(discord.ui.Modal, title="Modifier le salon vocal"):
    nom = discord.ui.TextInput(
        label="Nouveau nom du salon",
        placeholder="Ex: Salon de MonPseudo",
        max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
            if (channel.id in channel_owners and channel_owners[channel.id] == interaction.user.id) or interaction.user.guild_permissions.manage_channels:
                await channel.edit(name=str(self.nom))
                await interaction.response.send_message(f"✅ Salon renommé en **{self.nom}** !", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Tu n'es pas le propriétaire de ce salon vocal.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Tu n'es pas dans ton salon vocal.", ephemeral=True)

class KickSelect(discord.ui.Select):
    def __init__(self, channel: discord.VoiceChannel, owner_id: int):
        options = []
        for member in channel.members:
            if member.id != owner_id:
                options.append(discord.SelectOption(label=member.display_name, value=str(member.id), description=f"Expulser {member.name}"))
        if not options:
            options.append(discord.SelectOption(label="Personne à expulser", value="none", description="Aucun autre membre"))
        super().__init__(placeholder="Sélectionne un membre à expulser...", min_values=1, max_values=1, options=options)
        self.target_channel = channel
        self.owner_id = owner_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id and not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Seul le propriétaire peut expulser.", ephemeral=True)
            return
        if self.values[0] == "none":
            await interaction.response.send_message("❌ Personne à expulser.", ephemeral=True)
            return
        member = interaction.guild.get_member(int(self.values[0]))
        if member and member.voice and member.voice.channel == self.target_channel:
            await member.move_to(None)
            await interaction.response.send_message(f"👢 **{member.display_name}** a été expulsé !", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Ce membre n'est plus dans le salon.", ephemeral=True)

class KickView(discord.ui.View):
    def __init__(self, channel, owner_id):
        super().__init__(timeout=60)
        self.add_item(KickSelect(channel, owner_id))

class TransferSelect(discord.ui.Select):
    def __init__(self, channel: discord.VoiceChannel, current_owner_id: int):
        options = []
        for member in channel.members:
            if member.id != current_owner_id:
                options.append(discord.SelectOption(label=member.display_name, value=str(member.id), description=f"Transférer à {member.name}"))
        if not options:
            options.append(discord.SelectOption(label="Personne à qui transférer", value="none", description="Aucun autre membre"))
        super().__init__(placeholder="Sélectionne le nouveau propriétaire...", min_values=1, max_values=1, options=options)
        self.target_channel = channel
        self.current_owner_id = current_owner_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.current_owner_id and not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Seul le propriétaire actuel peut transférer.", ephemeral=True)
            return
        if self.values[0] == "none":
            await interaction.response.send_message("❌ Personne à qui transférer.", ephemeral=True)
            return
        new_owner = interaction.guild.get_member(int(self.values[0]))
        if new_owner and new_owner.voice and new_owner.voice.channel == self.target_channel:
            channel_owners[self.target_channel.id] = new_owner.id
            old_owner = interaction.guild.get_member(self.current_owner_id)
            if old_owner:
                await self.target_channel.set_permissions(old_owner, manage_channels=False, move_members=False, mute_members=False, deafen_members=False)
            await self.target_channel.set_permissions(new_owner, manage_channels=True, move_members=True, mute_members=True, deafen_members=True)
            await interaction.response.send_message(f"👑 Droits transférés à **{new_owner.display_name}** !", ephemeral=False)
        else:
            await interaction.response.send_message("❌ Ce membre n'est plus dans le salon.", ephemeral=True)

class TransferView(discord.ui.View):
    def __init__(self, channel, owner_id):
        super().__init__(timeout=60)
        self.add_item(TransferSelect(channel, owner_id))

class VocalControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Renommer", style=discord.ButtonStyle.primary, emoji="✏️", row=0)
    async def rename_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VocalControlModal())

    @discord.ui.button(label="Verrouiller/Ouvrir", style=discord.ButtonStyle.secondary, emoji="🔒", row=0)
    async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
            owner_id = channel_owners.get(channel.id)
            if interaction.user.id != owner_id and not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message("❌ Seul le propriétaire peut modifier.", ephemeral=True)
                return
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.connect = not overwrite.connect
            msg = "🔓 Salon ouvert." if overwrite.connect else "🔒 Salon verrouillé."
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message("❌ Tu n'es pas dans ton salon.", ephemeral=True)

    @discord.ui.button(label="Expulser", style=discord.ButtonStyle.danger, emoji="👢", row=1)
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
            owner_id = channel_owners.get(channel.id)
            if interaction.user.id != owner_id and not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message("❌ Seul le propriétaire peut expulser.", ephemeral=True)
                return
            await interaction.response.send_message("Choisis le membre à expulser :", view=KickView(channel, owner_id), ephemeral=True)
        else:
            await interaction.response.send_message("❌ Tu n'es pas dans ton salon.", ephemeral=True)

    @discord.ui.button(label="Transférer Admin", style=discord.ButtonStyle.success, emoji="👑", row=1)
    async def transfer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
            owner_id = channel_owners.get(channel.id)
            if interaction.user.id != owner_id and not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message("❌ Seul le propriétaire peut transférer.", ephemeral=True)
                return
            await interaction.response.send_message("Choisis le nouveau propriétaire :", view=TransferView(channel, owner_id), ephemeral=True)
        else:
            await interaction.response.send_message("❌ Tu n'es pas dans ton salon.", ephemeral=True)

class TempVocal(commands.Cog):
    TRIGGER_CHANNEL_NAME = "➕ Créer un vocal"

    def __init__(self, bot):
        self.bot = bot

    # Commande pour créer le salon manuellement quand tu veux
    @app_commands.command(name="setup-vocal", description="Crée automatiquement le salon de création vocale sur le serveur.")
    @app_commands.default_permissions(administrator=True)
    async def setup_vocal(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="COMMUNAUTÉ")
        if not category:
            category = await guild.create_category("COMMUNAUTÉ")

        existing_channel = discord.utils.get(guild.voice_channels, name=self.TRIGGER_CHANNEL_NAME)
        if existing_channel:
            await interaction.response.send_message("⚠️ Le salon de création existe déjà !", ephemeral=True)
        else:
            await guild.create_voice_channel(name=self.TRIGGER_CHANNEL_NAME, category=category)
            await interaction.response.send_message("✅ Le salon **➕ Créer un vocal** a été créé avec succès dans la catégorie COMMUNAUTÉ !", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if after.channel and after.channel.name == self.TRIGGER_CHANNEL_NAME:
            guild = member.guild
            category = after.channel.category
            channel_name = f"🔊 ┃ {member.display_name}"
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=True),
                member: discord.PermissionOverwrite(manage_channels=True, move_members=True, mute_members=True, deafen_members=True),
            }
            new_channel = await guild.create_voice_channel(name=channel_name, category=category, overwrites=overwrites)
            channel_owners[new_channel.id] = member.id
            await member.move_to(new_channel)
            try:
                await new_channel.send(f"🎛️ **Panneau de contrôle de ton salon, {member.mention}**", view=VocalControlView())
            except Exception:
                pass

        if before.channel and before.channel != after.channel:
            channel = before.channel
            if channel.name.startswith("🔊 ┃"):
                if len(channel.members) == 0:
                    channel_owners.pop(channel.id, None)
                    try:
                        await channel.delete()
                    except Exception:
                        pass
                else:
                    if channel_owners.get(channel.id) == member.id:
                        new_owner = channel.members[0]
                        channel_owners[channel.id] = new_owner.id
                        await channel.set_permissions(new_owner, manage_channels=True, move_members=True, mute_members=True, deafen_members=True)
                        try:
                            await channel.send(f"👑 **{member.display_name}** a quitté. Les droits passent à **{new_owner.display_name}** !")
                        except Exception:
                            pass

async def setup(bot):
    await bot.add_cog(TempVocal(bot))
