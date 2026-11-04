import asyncio
import time
import random
import discord
from discord import app_commands
from discord.ext import commands

import database as db


class Economie(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="solde",
        description="Affiche ton solde de pièces ou celui d'un autre membre",
    )
    async def solde(
        self, interaction: discord.Interaction, membre: discord.Member = None
    ):
        target = membre or interaction.user
        solde = await db.get_balance(target.id)
        rebirth_lvl = await db.get_user_rebirth(target.id)

        embed = discord.Embed(
            title=f"💰 Portefeuille de {target.display_name}",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Solde actuel", value=f"**{solde} pièces**", inline=True)
        if rebirth_lvl > 0:
            embed.add_field(name="Renaissance", value=f"Niveau `{rebirth_lvl}/3`", inline=True)
        
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="daily",
        description="Récupère ta récompense quotidienne de pièces",
    )
    async def daily(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = time.time()
        last_daily = await db.get_cooldown(user_id, "daily")

        if now - last_daily < 86400:
            temps_restant = 86400 - (now - last_daily)
            heures, minutes = int(temps_restant // 3600), int(
                (temps_restant % 3600) // 60
            )
            await interaction.response.send_message(
                f"⏳ Reviens dans **{heures}h et {minutes}min** pour ton prochain daily !",
                ephemeral=True,
            )
            return

        rebirth_lvl = await db.get_user_rebirth(user_id)
        montant = int(250 * (1.5 ** rebirth_lvl))

        await db.set_cooldown(user_id, "daily", now)
        await db.add_balance(user_id, montant)
        await interaction.response.send_message(
            f"🎁 Tu as récupéré ton bonus quotidien de **{montant} pièces** !"
        )

    @app_commands.command(
        name="work",
        description="Travaille pour gagner de l'argent (cooldown de 1 heure)",
    )
    async def work(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = time.time()
        last_work = await db.get_cooldown(user_id, "work")
        cooldown_time = 3600  # 1 heure

        if now - last_work < cooldown_time:
            temps_restant = cooldown_time - (now - last_work)
            minutes = int(temps_restant // 60)
            await interaction.response.send_message(
                f"⏳ Tu es fatigué ! Tu pourras re-travailler dans **{minutes} minutes**.",
                ephemeral=True,
            )
            return

        rebirth_lvl = await db.get_user_rebirth(user_id)
        salaire_base = random.randint(50, 150)
        salaire = int(salaire_base * (1.5 ** rebirth_lvl))

        jobs = [
            "développeur Discord",
            "streamer sur Twitch",
            "chasseur de bugs",
            "vendeur de café",
            "modérateur de serveur",
        ]
        job_choisi = random.choice(jobs)

        await db.set_cooldown(user_id, "work", now)
        await db.add_balance(user_id, salaire)

        await interaction.response.send_message(
            f"💼 Tu as travaillé en tant que **{job_choisi}** et tu as gagné **{salaire} pièces** !"
        )

    @app_commands.command(
        name="pay",
        description="Donne des pièces à un autre membre du serveur",
    )
    async def pay(
        self, interaction: discord.Interaction, membre: discord.Member, montant: int
    ):
        if montant <= 0:
            await interaction.response.send_message(
                "❌ Le montant doit être supérieur à 0.", ephemeral=True
            )
            return

        if membre.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Tu ne peux pas t'envoyer de l'argent à toi-même.", ephemeral=True
            )
            return

        sender_id = interaction.user.id
        solde_sender = await db.get_balance(sender_id)

        if solde_sender < montant:
            await interaction.response.send_message(
                f"❌ Tu n'as pas assez d'argent ! Ton solde : **{solde_sender} pièces**.",
                ephemeral=True,
            )
            return

        # Effectuer le transfert
        await db.add_balance(sender_id, -montant)
        await db.add_balance(membre.id, montant)

        await interaction.response.send_message(
            f"💸 {interaction.user.mention} a transféré avec succès **{montant} pièces** à {membre.mention} !"
        )

    @app_commands.command(
        name="coinflip",
        description="Parie tes pièces sur pile ou face",
    )
    @app_commands.choices(
        choix=[
            app_commands.Choice(name="Pile", value="pile"),
            app_commands.Choice(name="Face", value="face"),
        ]
    )
    async def coinflip(
        self, interaction: discord.Interaction, montant: int, choix: str
    ):
        user_id = interaction.user.id
        solde = await db.get_balance(user_id)

        if montant <= 0:
            await interaction.response.send_message(
                "❌ Le montant du pari doit être supérieur à 0.", ephemeral=True
            )
            return

        if solde < montant:
            await interaction.response.send_message(
                f"❌ Tu n'as pas assez d'argent pour ce pari ! Ton solde : **{solde} pièces**.",
                ephemeral=True,
            )
            return

        resultat = random.choice(["pile", "face"])

        if choix == resultat:
            gain = montant
            await db.add_balance(user_id, gain)
            await interaction.response.send_message(
                f"🪙 La pièce est tombée sur **{resultat}** !\n🎉 Gagné ! Tu remportes **{gain} pièces** !"
            )
        else:
            await db.add_balance(user_id, -montant)
            await interaction.response.send_message(
                f"🪙 La pièce est tombée sur **{resultat}**.\n❌ Perdu ! Tu perds tes **{montant} pièces**."
            )

import discord
from discord import app_commands
from discord.ext import commands

import database as db


class BoutiqueSelect(discord.ui.Select):

    def __init__(self, boutique_cog):
        self.boutique_cog = boutique_cog
        options = []
        for item_id, item_data in boutique_cog.articles.items():
            label = f"{item_data['nom']} - {item_data['prix']} pièces"
            description = item_data["description"][:50]
            emoji = item_data.get("emoji", "🛒")
            options.append(
                discord.SelectOption(
                    label=label,
                    value=item_id,
                    description=description,
                    emoji=emoji,
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="Aucun article disponible", value="none"
                )
            )

        super().__init__(
            placeholder="🛒 Choisis un article à acheter...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        item_id = self.values[0]
        if item_id == "none":
            await interaction.response.send_message(
                "❌ Aucun article en rayon pour le moment.", ephemeral=True
            )
            return
        await self.boutique_cog.effectuer_achat(interaction, item_id)


class BoutiqueView(discord.ui.View):

    def __init__(self, boutique_cog):
        super().__init__(timeout=None)
        self.add_item(BoutiqueSelect(boutique_cog))

    @discord.ui.button(emoji="❌", style=discord.ButtonStyle.danger, row=1)
    async def fermer_boutique(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.message.delete()

    @discord.ui.button(
        label="Mon Sac",
        emoji="🎒",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def mon_sac(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.client.get_cog("Boutique").afficher_inventaire(
            interaction
        )

    @discord.ui.button(
        label="Ma Fortune",
        emoji="💰",
        style=discord.ButtonStyle.success,
        row=1,
    )
    async def ma_fortune(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        solde = await db.get_balance(interaction.user.id)
        await interaction.response.send_message(
            f"💰 Tu possèdes actuellement **{solde} pièces**.", ephemeral=True
        )


class Boutique(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.articles = {
            "ticket_loterie": {
                "nom": "Ticket de Loterie",
                "prix": 200,
                "description": "Requis pour rejoindre les giveaways !",
                "emoji": "🎟️",
            }
        }

    async def effectuer_achat(self, interaction: discord.Interaction, item_id: str):
        solde = await db.get_balance(interaction.user.id)
        article = self.articles.get(item_id)

        if not article or solde < article["prix"]:
            await interaction.response.send_message(
                "❌ Fonds insuffisants ou article introuvable.", ephemeral=True
            )
            return

        await db.add_balance(interaction.user.id, -article["prix"])
        await db.add_inventory_item(interaction.user.id, item_id, 1)
        await interaction.response.send_message(
            f"🎉 Tu as acheté **{article['nom']}** !", ephemeral=True
        )

    @app_commands.command(
        name="boutique", description="Ouvre la boutique du serveur"
    )
    async def boutique_slash(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛒 BOUTIQUE DU SERVEUR", color=discord.Color.gold()
        )
        for item_id, data in self.articles.items():
            embed.add_field(
                name=f"{data['emoji']} {data['nom']} — `{data['prix']} pièces`",
                value=data["description"],
                inline=False,
            )
        await interaction.response.send_message(
            embed=embed, view=BoutiqueView(self)
        )

    async def afficher_inventaire(self, interaction_or_ctx):
        user = (
            interaction_or_ctx.user
            if isinstance(interaction_or_ctx, discord.Interaction)
            else interaction_or_ctx.author
        )
        user_inv = await db.get_inventory(user.id)
        embed = discord.Embed(
            title=f"🎒 Inventaire de {user.display_name}",
            color=discord.Color.purple(),
        )

        if not user_inv:
            embed.description = "Ton sac est totalement vide !"
        else:
            for item_id, qte in user_inv.items():
                art = self.articles.get(item_id, {})
                embed.add_field(
                    name=f"{art.get('emoji', '📦')} {art.get('nom', item_id)}",
                    value=f"Quantité : **{qte}**",
                )

        if isinstance(interaction_or_ctx, discord.Interaction):
            await interaction_or_ctx.response.send_message(
                embed=embed, ephemeral=True
            )
        else:
            await interaction_or_ctx.send(embed=embed)

    @app_commands.command(
        name="inventaire", description="Affiche ton sac d'objets"
    )
    async def inventaire_slash(self, interaction: discord.Interaction):
        await self.afficher_inventaire(interaction)

    import asyncio
import random
import re
import discord
from discord import app_commands
from discord.ext import commands

import database as db


class GiveawayView(discord.ui.View):

    def __init__(self, bot, duree_sec: int, lot: str, nb_gagnants: int):
        super().__init__(timeout=duree_sec)
        self.bot = bot
        self.lot = lot
        self.nb_gagnants = nb_gagnants
        self.participants = set()

    @discord.ui.button(
        label="Participer (1x 🎟️)",
        style=discord.ButtonStyle.primary,
        custom_id="gvo_join",
        emoji="🎟️",
    )
    async def rejoindre(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        user_id = interaction.user.id

        if user_id in self.participants:
            await interaction.response.send_message(
                "❌ Tu participes déjà à ce giveaway !", ephemeral=True
            )
            return

        retrait_reussi = await db.remove_inventory_item(
            user_id, "ticket_loterie", 1
        )
        if not retrait_reussi:
            await interaction.response.send_message(
                "❌ Tu n'as pas de **Ticket de Loterie** ! Achète-en un dans la `/boutique` pour participer.",
                ephemeral=True,
            )
            return

        self.participants.add(user_id)
        embed = interaction.message.embeds[0]
        embed.set_field_at(
            0,
            name="👥 Participants",
            value=f"**{len(self.participants)}** membre(s)",
            inline=True,
        )
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(
            "✅ Participation validée ! Un **Ticket de Loterie** 🎟️ a été retiré de ton sac.",
            ephemeral=True,
        )


class Giveaway(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gvo", description="Lance un giveaway")
    async def gvo(
        self,
        interaction: discord.Interaction,
        duree: str,
        lot: str,
        gagnants: int = 1,
    ):
        match = re.match(r"^(\d+)([s|m|h|d])$", duree.lower())
        if not match:
            await interaction.response.send_message(
                "❌ Durée invalide (ex: `30s`, `10m`, `2h`).", ephemeral=True
            )
            return

        unites = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        duree_sec = int(match.group(1)) * unites[match.group(2)]

        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=f"**Lot :** {lot}\n🎟️ **Condition :** 1x Ticket de Loterie",
            color=discord.Color.purple(),
        )
        embed.add_field(
            name="👥 Participants",
            value="**0** membre(s)",
            inline=True,
        )

        view = GiveawayView(self.bot, duree_sec, lot, gagnants)
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()

        await asyncio.sleep(duree_sec)
        if not view.participants:
            embed.description += "\n\n❌ Personne n'a participé."
            await msg.edit(embed=embed, view=None)
            return

        gagnants_ids = random.sample(
            list(view.participants), min(gagnants, len(view.participants))
        )
        mentions = [f"<@{uid}>" for uid in gagnants_ids]
        embed.description += f"\n\n🎊 **Gagnant(s) :** {', '.join(mentions)}"
        await msg.edit(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(Economie(bot))