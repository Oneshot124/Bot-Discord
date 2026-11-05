import discord
from discord import app_commands
from discord.ext import commands

import database as db

ADMIN_ROLE_IDS = [
    1562121971259539476,
]


class ClearConfirmView(discord.ui.View):

    def __init__(self, target_channel: discord.TextChannel):
        super().__init__(timeout=60)
        self.target_channel = target_channel

    @discord.ui.button(
        label="Oui", style=discord.ButtonStyle.danger, emoji="✅"
    )
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await self.target_channel.purge(limit=None)
            await interaction.followup.send(
                f"✅ **{len(deleted)} message(s)** supprimés dans {self.target_channel.mention}.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erreur lors de la suppression : {e}", ephemeral=True
            )
        self.stop()

    @discord.ui.button(
        label="Non", style=discord.ButtonStyle.secondary, emoji="❌"
    )
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "❌ Suppression annulée.", ephemeral=True
        )
        self.stop()


class Admin(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def est_admin(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        return any(
            role.id in ADMIN_ROLE_IDS for role in interaction.user.roles
        )

    async def log_action(
        self, interaction: discord.Interaction, description: str
    ):
        if not interaction.guild:
            return
        log_channel = discord.utils.get(
            interaction.guild.text_channels, name="log-economie"
        )
        if log_channel:
            embed = discord.Embed(
                title="📜 Log Administrateur",
                description=description,
                color=discord.Color.dark_grey(),
                timestamp=interaction.created_at,
            )
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url,
            )
            await log_channel.send(embed=embed)

    @app_commands.command(
        name="ban", description="Bannit un membre du serveur"
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        raison: str = "Aucune raison fournie",
    ):
        if not self.est_admin(interaction):
            await interaction.response.send_message(
                "❌ Permission insuffisante.", ephemeral=True
            )
            return

        if membre.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ Tu ne peux pas bannir ce membre car son rôle est supérieur ou égal au tien.",
                ephemeral=True,
            )
            return

        mp_envoye = True
        try:
            embed_mp = discord.Embed(
                title="🔨 Vous avez été banni",
                description=f"**Serveur :** {interaction.guild.name}\n**Raison :** {raison}\n**Modérateur :** {interaction.user.mention}",
                color=discord.Color.red(),
            )
            await membre.send(embed=embed_mp)
        except discord.Forbidden:
            mp_envoye = False

        try:
            await membre.ban(reason=f"{raison} (par {interaction.user})")
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erreur lors du bannissement : {e}", ephemeral=True
            )
            return

        reponse = f"🔨 {membre.mention} a été banni du serveur pour : **{raison}**"
        if not mp_envoye:
            reponse += "\n*(⚠️ Le MP n'a pas pu être envoyé : ses messages privés sont fermés).*"

        await interaction.response.send_message(reponse)
        await self.log_action(
            interaction,
            f"👤 **Admin :** {interaction.user.mention}\n🎯 **Cible :** {membre.mention} (`{membre.id}`)\n⚡ **Action :** Bannissement\n📜 **Raison :** {raison}",
        )

    @app_commands.command(
        name="clear",
        description="Supprime tous les messages d'un salon avec confirmation",
    )
    async def clear_channel(
        self, interaction: discord.Interaction, salon: discord.TextChannel
    ):
        if not self.est_admin(interaction):
            await interaction.response.send_message(
                "❌ Permission insuffisante.", ephemeral=True
            )
            return
        embed = discord.Embed(
            title="⚠️ Confirmation de nettoyage",
            description=f"Supprimer tous les messages du salon {salon.mention} ?",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(
            embed=embed, view=ClearConfirmView(salon), ephemeral=True
        )

    @app_commands.command(
        name="ajoute", description="Ajoute des pièces à un joueur"
    )
    async def ajoute_argent(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        montant: int,
    ):
        if not self.est_admin(interaction):
            await interaction.response.send_message(
                "❌ Permission insuffisante.", ephemeral=True
            )
            return
        await db.add_balance(membre.id, montant)
        await interaction.response.send_message(
            f"✅ **{montant} pièces** ajoutées au compte de {membre.mention}."
        )
        await self.log_action(
            interaction,
            f"👤 **Admin :** {interaction.user.mention}\n🎯 **Cible :** {membre.mention}\n⚡ **Action :** Ajout de **{montant} pièces**",
        )

    @app_commands.command(
        name="supprime", description="Retire des pièces à un joueur"
    )
    async def supprime_argent(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        montant: int,
    ):
        if not self.est_admin(interaction):
            await interaction.response.send_message(
                "❌ Permission insuffisante.", ephemeral=True
            )
            return
        await db.add_balance(membre.id, -montant)
        await interaction.response.send_message(
            f"✅ **{montant} pièces** retirées du compte de {membre.mention}."
        )
        await self.log_action(
            interaction,
            f"👤 **Admin :** {interaction.user.mention}\n🎯 **Cible :** {membre.mention}\n⚡ **Action :** Retrait de **{montant} pièces**",
        )

    @app_commands.command(
        name="reset", description="Remet l'argent d'un joueur à 0"
    )
    async def reset_argent(
        self, interaction: discord.Interaction, membre: discord.Member
    ):
        if not self.est_admin(interaction):
            await interaction.response.send_message(
                "❌ Permission insuffisante.", ephemeral=True
            )
            return
        await db.set_balance(membre.id, 0)
        await interaction.response.send_message(
            f"🧹 Solde de {membre.mention} réinitialisé à **0 pièce**."
        )

    @app_commands.command(
        name="ajoute-xp", description="Ajoute de l'XP à un membre"
    )
    async def ajoute_xp(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        montant: int,
    ):
        if not self.est_admin(interaction):
            await interaction.response.send_message(
                "❌ Permission insuffisante.", ephemeral=True
            )
            return
        xp, level, last_xp = await db.get_user_level_data(membre.id)
        nouveau_xp = max(0, xp + montant)
        nouveau_niveau = 0
        while nouveau_xp >= int(100 * ((nouveau_niveau + 1) ** 1.5)):
            nouveau_niveau += 1
        await db.update_user_level_data(
            membre.id, nouveau_xp, nouveau_niveau, last_xp
        )
        await interaction.response.send_message(
            f"✅ **+{montant} XP** ajoutés à {membre.mention} ! (Nouveau niveau : **{nouveau_niveau}**)"
        )

    @app_commands.command(
        name="retire-xp", description="Retire de l'XP à un membre"
    )
    async def retire_xp(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        montant: int,
    ):
        if not self.est_admin(interaction):
            await interaction.response.send_message(
                "❌ Permission insuffisante.", ephemeral=True
            )
            return
        xp, level, last_xp = await db.get_user_level_data(membre.id)
        nouveau_xp = max(0, xp - montant)
        nouveau_niveau = 0
        while nouveau_xp >= int(100 * ((nouveau_niveau + 1) ** 1.5)):
            nouveau_niveau += 1
        await db.update_user_level_data(
            membre.id, nouveau_xp, nouveau_niveau, last_xp
        )
        await interaction.response.send_message(
            f"✅ **-{montant} XP** retirés à {membre.mention}. (Nouveau niveau : **{nouveau_niveau}**)"
        )

    @app_commands.command(
        name="warn", description="Donne un avertissement à un membre"
    )
    async def warn(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        raison: str,
    ):
        if not self.est_admin(interaction):
            await interaction.response.send_message(
                "❌ Permission insuffisante.", ephemeral=True
            )
            return

        await db.add_warn(membre.id, raison, interaction.user.id)

        mp_envoye = True
        try:
            embed_mp = discord.Embed(
                title="⚠️ Vous avez reçu un avertissement",
                description=f"**Serveur :** {interaction.guild.name}\n**Raison :** {raison}\n**Modérateur :** {interaction.user.mention}",
                color=discord.Color.orange(),
            )
            await membre.send(embed=embed_mp)
        except discord.Forbidden:
            mp_envoye = False

        reponse = f"⚠️ {membre.mention} a été averti pour : **{raison}**"
        if not mp_envoye:
            reponse += "\n*(⚠️ Le MP n'a pas pu être envoyé : ses messages privés sont fermés).*"

        await interaction.response.send_message(reponse)

    @app_commands.command(
        name="creer-role",
        description="Crée un rôle avec une couleur hex et une icône optionnelle",
    )
    async def creer_role(
        self,
        interaction: discord.Interaction,
        nom: str,
        icone: discord.Attachment = None,
        couleur: str = "#99AAB5",
    ):
        if not self.est_admin(interaction):
            await interaction.response.send_message(
                "❌ Permission insuffisante.", ephemeral=True
            )
            return

        await interaction.response.defer()
        try:
            color_obj = discord.Color.from_str(couleur)
        except ValueError:
            await interaction.followup.send(
                "❌ Code couleur Hex invalide (ex: `#FF0000`).", ephemeral=True
            )
            return

        icon_bytes = await icone.read() if icone else None
        try:
            role = await interaction.guild.create_role(
                name=nom, color=color_obj, display_icon=icon_bytes
            )
            await interaction.followup.send(
                f"🎭 Rôle {role.mention} créé avec succès !"
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Erreur lors de la création : {e}", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Admin(bot))
