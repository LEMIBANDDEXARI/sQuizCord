import os
import interactions
import asyncio
import json
import random
from interactions import slash_command, SlashContext
from discord.ext import commands

bot = interactions.Client()

# Liste des utilisateurs qui ont rejoint la partie
players = []

@interactions.listen()
async def on_startup():
    print("Le bot est prêt !")

@slash_command(
    name="rejoindre",
    description="Pour rejoindre une partie.",
)
async def join(ctx: SlashContext):
    if ctx.author not in players:
        players.append(ctx.author)
        await ctx.send(f"{ctx.author.username} a rejoint la partie.")  # Utilisez 'username' au lieu de 'name'
    else:
        await ctx.send("Vous avez déjà rejoint la partie.")

@slash_command(
    name="partir",
    description="Pour quitter une partie.",
)
async def leave(ctx: SlashContext):
    if ctx.author in players:
        players.remove(ctx.author)
        await ctx.send(f"{ctx.author.username} a quitté la partie.")  # Utilisez 'username' au lieu de 'name'
    else:
        await ctx.send("Vous n'avez pas rejoint la partie.")

# Ajouter une variable pour stocker l'utilisateur qui a lancé la partie
game_starter = None
# Ajouter une variable pour suivre si une partie est en cours
game_in_progress = False
# Ajouter une variable pour suivre si le jeu doit être arrêté
game_should_end = False
class GameEndException(Exception):# Ajouter une exception personnalisée pour arrêter la partie
    pass

@slash_command(
    name="start",
    description="Pour commencer une partie.",
)
async def start(ctx: SlashContext):
    global game_starter, game_in_progress, game_should_end
    game_should_end = False  # Réinitialiser l'état d'arrêt du jeu
    if game_in_progress:
        await ctx.send("Une partie est déjà en cours.")
        return
    game_starter = ctx.author
    game_in_progress = True
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
        await ctx.send("La partie a été interrompue.")
        return

    await ctx.send("Fin de la partie.")  # Afficher "fin de la partie" à la fin

@slash_command(
    name="end",
    description="Pour mettre fin à une partie.",
)
async def end(ctx: SlashContext):
    global game_starter, game_in_progress, game_should_end
    if game_in_progress:  # Vérifier si une partie est en cours
        if ctx.author == game_starter:  # Vérifier si l'utilisateur qui tente de mettre fin à la partie est celui qui l'a commencée
            game_starter = None  # Réinitialiser l'utilisateur qui a lancé la partie
            game_in_progress = False  # Indiquer qu'aucune partie n'est en cours
            game_should_end = True  # Indiquer que le jeu doit être arrêté
        else:
            await ctx.send("Seul l'utilisateur qui a lancé la partie peut la terminer.")
    else:
        await ctx.send("Aucune partie n'est en cours.")  # Indiquer qu'aucune partie n'est en cours si l'utilisateur tente de mettre fin à une partie qui n'a pas commencé

bot.start(os.getenv('DISCORD_TOKEN'))