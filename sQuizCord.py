import os
import interactions
import asyncio
import json
import random
import discord
from interactions import slash_command, SlashContext
from discord.ext import commands

bot = interactions.Client()

# Liste des utilisateurs qui ont rejoint la partie
players = []

async def check_players():
    global game_in_progress
    while True:
        await asyncio.sleep(1)  # Attendre une seconde
        if game_in_progress and not players:
            game_in_progress = False
            if game_channel:  # Vérifier si le canal de jeu est défini
                break  # Arrêter la boucle si la partie est terminée

@interactions.listen()
async def on_startup():
    print("Le bot est prêt !")
    # Lancer la tâche de vérification des joueurs après la définition de votre bot
    asyncio.create_task(check_players())
    print(f'Je suis connecté en tant que {bot.user}')
    servers = list(bot.guilds)
    print(f"Connecté sur {len(servers)} serveurs:")
    for server in servers:
        print(f"- {server.name}")

@slash_command(
    name="rejoindre",
    description="Pour rejoindre une partie.",
)
async def join(ctx: SlashContext):
    global player_role
    if ctx.author not in players:
        players.append(ctx.author)
        # Ajouter le rôle "en jeu" à l'utilisateur qui rejoint la partie
        player_role = discord.utils.get(ctx.guild.roles, name="en jeu")
        if player_role:
            await ctx.author.add_roles([player_role])
        await ctx.send(f"{ctx.author.username} a rejoint la partie.")  # Utilisez 'username' au lieu de 'name'
    else:
        await ctx.send("Vous avez déjà rejoint la partie.")

@slash_command(
    name="partir",
    description="Pour quitter une partie.",
)
async def leave(ctx: SlashContext):
    global game_in_progress, player_role
    if ctx.author in players:
        players.remove(ctx.author)
        # Retirer le rôle "joueur" de l'utilisateur qui quitte la partie
        if player_role:
            await ctx.author.remove_roles([player_role])
        await ctx.send(f"{ctx.author.username} a quitté la partie.")  # Utilisez 'username' au lieu de 'name'
        # Si tous les joueurs ont quitté la partie, réinitialiser game_in_progress à False
        if not players:
            game_in_progress = False
            await ctx.send("La partie a été fermée car tous les joueurs ont quitté la partie.")
    else:
        await ctx.send("Vous n'avez pas rejoint la partie.")

# Variable globale pour stocker le canal de jeu
game_channel = None
player_role = None  # Ajouter une variable pour stocker le rôle "en jeu"
# Ajouter une variable pour suivre si une partie est en cours
game_in_progress = False
# Ajouter une variable pour suivre si le jeu doit être arrêté
game_should_end = False
class GameEndException(Exception):# Ajouter une exception personnalisée pour arrêter la partie
    pass

game_master_role = None  # Ajouter une variable pour stocker le rôle "game-master"

@slash_command(
    name="game-master",
    description="Pour devenir ou cesser d'être le game-master.",
)
async def game_master(ctx: SlashContext):
    global game_master_role
    game_master_role = discord.utils.get(ctx.guild.roles, name="game-master")
    if game_master_role in ctx.author.roles:
        await ctx.author.remove_roles([game_master_role])
        await ctx.send(f"{ctx.author.username} n'est plus le game-master.")
    else:
        if any(game_master_role in member.roles for member in ctx.guild.members):
            await ctx.send("Il y a déjà un game-master.")
        else:
            await ctx.author.add_roles([game_master_role])
            await ctx.send(f"{ctx.author.username} est maintenant le game-master.")

@slash_command(
    name="start",
    description="Pour commencer une partie.",
)
async def start(ctx: SlashContext):
    global game_starter, game_in_progress, game_should_end, game_ended_by_starter, game_channel, game_master_role
    game_master_role = discord.utils.get(ctx.guild.roles, name="game-master")
    if game_master_role not in ctx.author.roles:
        await ctx.send("Seul le game-master peut commencer une partie.")
        return
    game_channel = ctx.channel  # Stocker le canal de jeu
    game_should_end = False  # Réinitialiser l'état d'arrêt du jeu
    if game_in_progress and not game_ended_by_starter:
        await ctx.send("Une partie est déjà en cours.")
        return
    game_starter = ctx.author
    game_in_progress = True
    # Ajouter ici la réinitialisation de game_ended_by_starter
    game_ended_by_starter = False
    if not players:
        await ctx.send("Aucun joueur n'a rejoint la partie.")
        return

    # Charger les questions à partir d'un fichier JSON
    with open('questions.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)

    # Sélectionner un échantillon unique de 5 questions
    selected_questions = random.sample(questions, 5)

    message = await ctx.send("La partie va commencer dans 20 secondes.")
    for i in range(19, 0, -1):
        await asyncio.sleep(1)
        if game_should_end or not players:  # Vérifier si le jeu doit être arrêté ou si tous les joueurs ont quitté
            await ctx.send("La partie a été arrêté.")
            game_in_progress = False
            return
        if i == 1:
            await message.edit(content="La partie commence.")
        else:
            await message.edit(content=f"La partie va commencer dans {i-1} secondes.")

    try:
        for question in selected_questions:  # Boucle pour poser 5 questions
            if game_should_end:  # Vérifier si le jeu doit être arrêté
                await ctx.send("La partie a été arrêté.")
                return
            question_text = question['question']
            category = question['category']
            correct_answer = question['answer']  # Assurez-vous que votre fichier JSON contient un champ 'answer' pour chaque question

            question_message = await ctx.send(content=f"Catégorie : {category}\n{question_text}\n\n15 secondes pour répondre")
            player_answer = None
            for i in range(14, -1, -1):
                await asyncio.sleep(1)
                if game_should_end:  # Vérifier si le jeu doit être arrêté
                    raise GameEndException()
                await question_message.edit(content=f"Catégorie : {category}\n{question_text}\n\n{i} secondes pour répondre")

            # Attendre la réponse du joueur
            def check(m):
                result = m.author in players and m.channel == ctx.channel
                print(f"Checking message from {m.author}: {m.content}. Result: {result}")
                return result

            player_answer = None
            for i in range(15, 0, -1):
                try:
                    print("Waiting for player's answer...")  # Ajout pour le débogage
                    message = await bot.wait_for('message', timeout=1.0)  # Attendre 1 seconde pour une réponse
                    print("Received a message:", message.content)  # Ajout pour le débogage
                    if check(message):
                        player_answer = message
                        break
                except asyncio.TimeoutError:
                    if game_should_end:  # Vérifier si le jeu doit être arrêté
                        raise GameEndException()
                    continue

        if player_answer is not None:
            print(player_answer.content.lower(), correct_answer.lower())  # Ajout pour le débogage
            if player_answer.content.lower() == correct_answer.lower():  # Comparer les réponses en minuscules pour éviter les problèmes de casse
                await ctx.send("Félicitations, vous avez la bonne réponse !")
            else:
                await ctx.send("Désolé, ce n'est pas la bonne réponse.")
        else:
            await ctx.send(f"Temps écoulé\nLa réponse était : {correct_answer}")
            await asyncio.sleep(15)  # Ajout d'un décompte de 15 secondes
    except GameEndException:
        game_in_progress = False  # Réinitialiser l'état du jeu ici
        await ctx.send("La partie a été interrompue.")
        return

    game_in_progress = False  # Réinitialiser l'état du jeu ici aussi, si le jeu se termine normalement
    await ctx.send("Fin de la partie.")  # Afficher "fin de la partie" à la fin

@slash_command(
    name="end",
    description="Pour mettre fin à une partie.",
)
async def end(ctx: SlashContext):
    global game_starter, game_in_progress, game_should_end, game_ended_by_starter
    if game_in_progress and game_starter is not None:  # Vérifier si une partie est en cours et si game_starter n'est pas None
        if ctx.author.id == game_starter.id:  # Vérifier si l'utilisateur qui tente de mettre fin à la partie est celui qui l'a commencée
            game_starter = None  # Réinitialiser l'utilisateur qui a lancé la partie
            game_should_end = True  # Indiquer que le jeu doit être arrêté
            game_ended_by_starter = True  # Indiquer que la partie a été terminée par l'utilisateur qui l'a lancée
            game_in_progress = False  # Réinitialiser l'état du jeu ici
        else:
            await ctx.send("Seul l'utilisateur qui a lancé la partie peut la terminer.")
            return  # Ajouter un return ici pour arrêter l'exécution de la fonction si l'utilisateur n'est pas celui qui a commencé la partie
    elif not game_in_progress or (game_starter is None and not game_ended_by_starter):  # Ajout de cette condition pour vérifier si aucune partie n'est en cours ou si game_starter est None et la partie n'a pas été terminée par l'utilisateur qui l'a lancée
        await ctx.send("Aucune partie n'est en cours.")  # Indiquer qu'aucune partie n'est en cours si l'utilisateur tente de mettre fin à une partie qui n'a pas commencé

bot.start(os.getenv('DISCORD_TOKEN'))