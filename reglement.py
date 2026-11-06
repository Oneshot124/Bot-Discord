import discord
from discord.ext import commands
from discord import app_commands

class RulesButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="J'accepte le règlement", 
        style=discord.ButtonStyle.success, 
        emoji="✅", 
        custom_id="persistent_accept_rules"
    )
    async def accept_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ⚠️ MODIFIE "Membre" ci-dessous par le nom EXACT de ton rôle sur Discord !
        nom_du_role = "✅・Membre" 
        
        role = discord.utils.get(interaction.guild.roles, name=nom_du_role)
        
        if not role:
            await interaction.response.send_message(
                f"❌ Le rôle **{nom_du_role}** est introuvable sur ce serveur. Vérifie son orthographe dans le code !", 
                ephemeral=True
            )
            return
        
        if role in interaction.user.roles:
            await interaction.response.send_message("ℹ️ Tu as déjà accepté le règlement !", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Règlement accepté avec succès ! Bon jeu sur le serveur 🎉", ephemeral=True)

class Reglement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(RulesButtonView())

    @app_commands.command(name="message-staff", description="Envoie le message de règlement avec un bouton d'acceptation interactif.")
    @app_commands.describe(texte="Le texte du règlement que tu veux envoyer")
    @app_commands.default_permissions(administrator=True)
    async def message_staff(self, interaction: discord.Interaction, texte: str):
        view = RulesButtonView()
        
        embed = discord.Embed(
            title="📜 Règlement de E x L's Community",
            description=texte,
            color=discord.Color.blue()
        )
        embed.set_footer(text="Clique sur le bouton ci-dessous pour débloquer l'accès au serveur.")

        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Le message de règlement a été généré et envoyé avec succès !", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Reglement(bot))
