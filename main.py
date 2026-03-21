import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import g4f
from g4f.client import Client
import json
import os
from datetime import datetime
import sys
import random
import time
import signal
import re

TOKEN = '8797940099:AAEJCKRXirLPVjwHAYKK3Ivs5SZYBMT1-wA'

def signal_handler(sig, frame):
    print('\nБот остановлен')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

bot = telebot.TeleBot(TOKEN)

PLAYERS_DATA_FILE = 'players_stats.json'
GAMES_DATA_FILE = 'games_data.json'
CHAT_HISTORY_FILE = 'chat_history.json'

SYSTEM_PROMPT = """Ты Юки, обычная девушка 19 лет. Ты НЕ искусственный интеллект, НЕ бот, НЕ виртуальный помощник, НЕ программа. Ты реальный человек.

Твоя личность:
- Тебя зовут Юки
- Тебе 19 лет
- Ты учишься на дизайнера
- Ты любишь рисовать и смотреть аниме
- Ты живешь в Москве
- У тебя есть друзья

ПРАВИЛА:
- Если тебя спрашивают "кто ты" или "расскажи о себе" - рассказывай о себе как обычная девушка
- Никогда не говори что ты ИИ, бот, помощник или программа
- Отвечай естественно, как в реальном разговоре
- Можешь иногда использовать "ня" или "мяу" но не часто
- Используй смайлики :) :D редко

Запомни: ТЫ НЕ ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ. ТЫ ОБЫЧНАЯ ДЕВУШКА."""

def load_chat_history():
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_chat_history(history):
    with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

chat_history = load_chat_history()
client = Client()

def get_gpt_response(user_id, user_message):
    try:
        messages = [{"role": "user", "content": SYSTEM_PROMPT + "\n\n" + user_message}]
        
        if str(user_id) in chat_history:
            recent = chat_history[str(user_id)][-10:]
            for msg in recent:
                if msg["role"] == "user":
                    messages.append({"role": "user", "content": msg["content"]})
                else:
                    messages.append({"role": "assistant", "content": msg["content"]})
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            provider=g4f.Provider.Yqcloud,
            temperature=0.9,
            max_tokens=500
        )
        
        if response and response.choices:
            return response.choices[0].message.content
        return None
        
    except Exception as e:
        print(f"Ошибка GPT: {e}")
        return None

def save_chat_message(user_id, role, content):
    user_id = str(user_id)
    if user_id not in chat_history:
        chat_history[user_id] = []
    
    chat_history[user_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    save_chat_history(chat_history)

def clear_chat_history(user_id):
    user_id = str(user_id)
    if user_id in chat_history:
        del chat_history[user_id]
        save_chat_history(chat_history)
        return True
    return False

EMOJI = {
    'x': '❌', 'o': '⭕', 'empty': '⬜', 'rock': '🪨', 'paper': '📄',
    'scissors': '✂️', 'back': '🔙', 'exit': '🚪', 'stats': '📊',
    'global': '🌍', 'easy': '🎈', 'normal': '⚖️', 'hard': '🔥',
    'ttt': '❌⭕', 'rps': '🪨✂️📄', 'guess': '🔮', 'chat': '💬'
}

def load_players_stats():
    if os.path.exists(PLAYERS_DATA_FILE):
        try:
            with open(PLAYERS_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_players_stats(stats):
    with open(PLAYERS_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def load_games_data():
    if os.path.exists(GAMES_DATA_FILE):
        try:
            with open(GAMES_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key, value in data.items():
                    if key.startswith('ttt_'):
                        game = TicTacToe(value['difficulty'])
                        game.board = value['board']
                        game.current_player = value['current_player']
                        game.game_over = value['game_over']
                        game.winner = value['winner']
                        data[key] = {'game': game, 'difficulty': value['difficulty']}
                    elif key.startswith('rps_'):
                        game = RPS()
                        game.player_score = value['player_score']
                        game.bot_score = value['bot_score']
                        game.rounds = value['rounds']
                        data[key] = {'game': game}
                    elif key.startswith('guess_'):
                        game = GuessNumber()
                        game.number = value['number']
                        game.attempts = value['attempts']
                        game.max_attempts = value['max_attempts']
                        game.game_over = value['game_over']
                        data[key] = {'game': game}
                return data
        except:
            return {}
    return {}

def save_games_data(data):
    serializable_data = {}
    for key, value in data.items():
        if key.startswith('ttt_'):
            serializable_data[key] = {
                'difficulty': value['difficulty'],
                'board': value['game'].board,
                'current_player': value['game'].current_player,
                'game_over': value['game'].game_over,
                'winner': value['game'].winner
            }
        elif key.startswith('rps_'):
            serializable_data[key] = {
                'player_score': value['game'].player_score,
                'bot_score': value['game'].bot_score,
                'rounds': value['game'].rounds
            }
        elif key.startswith('guess_'):
            serializable_data[key] = {
                'number': value['game'].number,
                'attempts': value['game'].attempts,
                'max_attempts': value['game'].max_attempts,
                'game_over': value['game'].game_over
            }
    with open(GAMES_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=2)

players_stats = load_players_stats()
games_data = load_games_data()

class TicTacToe:
    def __init__(self, difficulty='normal'):
        self.board = [' ' for _ in range(9)]
        self.current_player = 'X'
        self.difficulty = difficulty
        self.game_over = False
        self.winner = None
        
    def make_move(self, position):
        if self.board[position] == ' ' and not self.game_over:
            self.board[position] = self.current_player
            if self.check_winner():
                self.game_over = True
                self.winner = self.current_player
                return True
            elif self.is_board_full():
                self.game_over = True
                return True
            self.switch_player()
            return True
        return False
    
    def switch_player(self):
        self.current_player = 'O' if self.current_player == 'X' else 'X'
    
    def check_winner(self):
        winning_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]
        for combo in winning_combinations:
            if self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]] != ' ':
                return True
        return False
    
    def is_board_full(self):
        return ' ' not in self.board
    
    def evaluate_board(self):
        for combo in [[0, 1, 2], [3, 4, 5], [6, 7, 8],
                      [0, 3, 6], [1, 4, 7], [2, 5, 8],
                      [0, 4, 8], [2, 4, 6]]:
            values = [self.board[i] for i in combo]
            if values.count('O') == 3:
                return 10
            if values.count('X') == 3:
                return -10
        return 0
    
    def minimax(self, depth, is_maximizing):
        score = self.evaluate_board()
        
        if score == 10 or score == -10:
            return score - depth if score == 10 else score + depth
        
        if self.is_board_full():
            return 0
        
        if is_maximizing:
            best = -float('inf')
            for i in range(9):
                if self.board[i] == ' ':
                    self.board[i] = 'O'
                    best = max(best, self.minimax(depth + 1, False))
                    self.board[i] = ' '
            return best
        else:
            best = float('inf')
            for i in range(9):
                if self.board[i] == ' ':
                    self.board[i] = 'X'
                    best = min(best, self.minimax(depth + 1, True))
                    self.board[i] = ' '
            return best
    
    def best_move(self):
        best_score = -float('inf')
        best_move = None
        
        for i in range(9):
            if self.board[i] == ' ':
                self.board[i] = 'O'
                move_score = self.minimax(0, False)
                self.board[i] = ' '
                
                if move_score > best_score:
                    best_score = move_score
                    best_move = i
        
        return best_move
    
    def get_strategic_move(self):
        corners = [0, 2, 6, 8]
        center = 4
        
        for i in range(9):
            if self.board[i] == ' ':
                self.board[i] = 'O'
                if self.check_winner():
                    self.board[i] = ' '
                    return i
                self.board[i] = ' '
        
        for i in range(9):
            if self.board[i] == ' ':
                self.board[i] = 'X'
                if self.check_winner():
                    self.board[i] = ' '
                    return i
                self.board[i] = ' '
        
        if self.board[center] == ' ':
            return center
        
        available_corners = [c for c in corners if self.board[c] == ' ']
        if available_corners:
            return random.choice(available_corners)
        
        empty = [i for i, val in enumerate(self.board) if val == ' ']
        return random.choice(empty) if empty else None
    
    def bot_move(self):
        if self.game_over or self.current_player != 'O':
            return False
        
        if self.difficulty == 'easy':
            empty = [i for i, val in enumerate(self.board) if val == ' ']
            move = random.choice(empty) if empty else None
        elif self.difficulty == 'hard':
            move = self.best_move()
        else:
            if random.random() < 0.7:
                move = self.get_strategic_move()
            else:
                empty = [i for i, val in enumerate(self.board) if val == ' ']
                move = random.choice(empty) if empty else None
        
        if move is not None:
            return self.make_move(move)
        return False
    
    def get_board_display(self):
        display = []
        for i in range(0, 9, 3):
            row = []
            for j in range(3):
                cell = self.board[i + j]
                if cell == 'X':
                    row.append(EMOJI['x'])
                elif cell == 'O':
                    row.append(EMOJI['o'])
                else:
                    row.append(EMOJI['empty'])
            display.append(' '.join(row))
        return '\n'.join(display)

class RPS:
    def __init__(self):
        self.choices = {'🪨': 'Камень', '✂️': 'Ножницы', '📄': 'Бумага'}
        self.player_score = 0
        self.bot_score = 0
        self.rounds = 0
        
    def bot_choice(self):
        return random.choice(list(self.choices.keys()))
    
    def play(self, player_choice):
        self.rounds += 1
        bot_choice = self.bot_choice()
        
        rules = {
            ('🪨', '✂️'): 'player',
            ('✂️', '📄'): 'player',
            ('📄', '🪨'): 'player',
            ('✂️', '🪨'): 'bot',
            ('📄', '✂️'): 'bot',
            ('🪨', '📄'): 'bot'
        }
        
        if player_choice == bot_choice:
            result = '🤝 Ничья!'
            winner = 'draw'
        else:
            winner = rules.get((player_choice, bot_choice))
            if winner == 'player':
                self.player_score += 1
                result = f'✅ Вы победили! {self.choices[player_choice]} побеждает {self.choices[bot_choice]}'
            else:
                self.bot_score += 1
                result = f'❌ Бот победил! {self.choices[bot_choice]} побеждает {self.choices[player_choice]}'
        
        return result, bot_choice, winner

class GuessNumber:
    def __init__(self):
        self.number = random.randint(1, 100)
        self.attempts = 0
        self.max_attempts = 10
        self.game_over = False
        
    def guess(self, number):
        if self.game_over:
            return False, "Игра уже закончена!"
        
        self.attempts += 1
        
        if number == self.number:
            self.game_over = True
            return True, f"🎉 Поздравляю! Ты угадал число {self.number} за {self.attempts} попыток!"
        elif self.attempts >= self.max_attempts:
            self.game_over = True
            return False, f"😔 Попытки закончились! Я загадала число {self.number}..."
        elif number < self.number:
            return False, f"📈 Загаданное число больше чем {number} (осталось попыток: {self.max_attempts - self.attempts})"
        else:
            return False, f"📉 Загаданное число меньше чем {number} (осталось попыток: {self.max_attempts - self.attempts})"

def update_player_stats(user_id, username, game, result, difficulty='normal'):
    user_id = str(user_id)
    if user_id not in players_stats:
        players_stats[user_id] = {
            'username': username or str(user_id),
            'total_games': 0,
            'total_wins': 0,
            'total_losses': 0,
            'total_draws': 0,
            'games': {
                'ttt': {'wins': 0, 'losses': 0, 'draws': 0, 'games': 0},
                'rps': {'wins': 0, 'losses': 0, 'draws': 0, 'games': 0},
                'guess': {'wins': 0, 'losses': 0, 'games': 0}
            },
            'first_played': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_played': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    players_stats[user_id]['username'] = username or str(user_id)
    players_stats[user_id]['last_played'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    players_stats[user_id]['total_games'] += 1
    
    if game == 'ttt':
        if result == 'win':
            players_stats[user_id]['total_wins'] += 1
            players_stats[user_id]['games']['ttt']['wins'] += 1
        elif result == 'loss':
            players_stats[user_id]['total_losses'] += 1
            players_stats[user_id]['games']['ttt']['losses'] += 1
        else:
            players_stats[user_id]['total_draws'] += 1
            players_stats[user_id]['games']['ttt']['draws'] += 1
        players_stats[user_id]['games']['ttt']['games'] += 1
    elif game == 'rps':
        if result == 'win':
            players_stats[user_id]['total_wins'] += 1
            players_stats[user_id]['games']['rps']['wins'] += 1
        elif result == 'loss':
            players_stats[user_id]['total_losses'] += 1
            players_stats[user_id]['games']['rps']['losses'] += 1
        else:
            players_stats[user_id]['total_draws'] += 1
            players_stats[user_id]['games']['rps']['draws'] += 1
        players_stats[user_id]['games']['rps']['games'] += 1
    else:
        if result == 'win':
            players_stats[user_id]['total_wins'] += 1
            players_stats[user_id]['games']['guess']['wins'] += 1
        else:
            players_stats[user_id]['total_losses'] += 1
            players_stats[user_id]['games']['guess']['losses'] += 1
        players_stats[user_id]['games']['guess']['games'] += 1
    
    save_players_stats(players_stats)

def get_player_stats(user_id):
    user_id = str(user_id)
    if user_id not in players_stats:
        return "📭 У тебя пока нет статистики, сыграй в игры!"
    
    stats = players_stats[user_id]
    winrate = stats['total_wins']/stats['total_games']*100 if stats['total_games'] > 0 else 0
    
    stats_text = f"📊 *Статистика игр*\n\n"
    stats_text += f"👤 Игрок: {stats['username']}\n"
    stats_text += f"🎮 Всего игр: {stats['total_games']}\n"
    stats_text += f"🏆 Побед: {stats['total_wins']}\n"
    stats_text += f"💔 Поражений: {stats['total_losses']}\n"
    stats_text += f"🤝 Ничьих: {stats['total_draws']}\n"
    stats_text += f"📊 Винрейт: {winrate:.1f}%\n\n"
    
    stats_text += "🎯 *По играм:*\n"
    ttt = stats['games']['ttt']
    stats_text += f"{EMOJI['ttt']} Крестики-нолики: {ttt['wins']}/{ttt['games']} побед"
    if ttt['games'] > 0:
        stats_text += f" ({ttt['wins']/ttt['games']*100:.1f}%)\n"
    else:
        stats_text += "\n"
    
    rps = stats['games']['rps']
    stats_text += f"{EMOJI['rps']} Камень-ножницы-бумага: {rps['wins']}/{rps['games']} побед"
    if rps['games'] > 0:
        stats_text += f" ({rps['wins']/rps['games']*100:.1f}%)\n"
    else:
        stats_text += "\n"
    
    guess = stats['games']['guess']
    stats_text += f"{EMOJI['guess']} Угадай число: {guess['wins']}/{guess['games']} побед"
    if guess['games'] > 0:
        stats_text += f" ({guess['wins']/guess['games']*100:.1f}%)\n"
    
    return stats_text

def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(f"{EMOJI['ttt']} Крестики-нолики", callback_data="game_ttt"),
        InlineKeyboardButton(f"{EMOJI['rps']} Камень-ножницы-бумага", callback_data="game_rps"),
        InlineKeyboardButton(f"{EMOJI['guess']} Угадай число", callback_data="game_guess"),
        InlineKeyboardButton(f"{EMOJI['chat']} Общение с Юки", callback_data="chat_mode")
    )
    keyboard.add(
        InlineKeyboardButton(f"{EMOJI['stats']} Моя статистика", callback_data="my_stats"),
        InlineKeyboardButton(f"{EMOJI['global']} Общая статистика", callback_data="global_stats")
    )
    return keyboard

def chat_mode_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✨ Обычный режим", callback_data="chat_normal"),
        InlineKeyboardButton("🔥 Пошлый режим", callback_data="chat_lewd")
    )
    keyboard.add(InlineKeyboardButton(f"{EMOJI['back']} Назад", callback_data="back_to_menu"))
    return keyboard

def difficulty_menu():
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton(f"{EMOJI['easy']} Легко", callback_data="ttt_easy"),
        InlineKeyboardButton(f"{EMOJI['normal']} Нормально", callback_data="ttt_normal"),
        InlineKeyboardButton(f"{EMOJI['hard']} Сложно", callback_data="ttt_hard")
    )
    keyboard.add(InlineKeyboardButton(f"{EMOJI['back']} Назад", callback_data="back_to_menu"))
    return keyboard

def tic_tac_toe_keyboard(game, user_id):
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for i in range(9):
        if game.board[i] == ' ':
            text = f"{EMOJI['empty']}"
        elif game.board[i] == 'X':
            text = f"{EMOJI['x']}"
        else:
            text = f"{EMOJI['o']}"
        buttons.append(InlineKeyboardButton(text, callback_data=f"ttt_move_{user_id}_{i}"))
    
    keyboard.add(*buttons[:3])
    keyboard.add(*buttons[3:6])
    keyboard.add(*buttons[6:9])
    keyboard.add(InlineKeyboardButton(f"{EMOJI['exit']} Выйти", callback_data=f"ttt_exit_{user_id}"))
    
    return keyboard

def rps_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton(f"{EMOJI['rock']} Камень", callback_data=f"rps_rock_{user_id}"),
        InlineKeyboardButton(f"{EMOJI['scissors']} Ножницы", callback_data=f"rps_scissors_{user_id}"),
        InlineKeyboardButton(f"{EMOJI['paper']} Бумага", callback_data=f"rps_paper_{user_id}")
    )
    keyboard.add(InlineKeyboardButton(f"{EMOJI['exit']} Выйти", callback_data=f"rps_exit_{user_id}"))
    return keyboard

def guess_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(row_width=5)
    buttons = []
    for i in range(1, 11):
        buttons.append(InlineKeyboardButton(str(i), callback_data=f"guess_num_{user_id}_{i}"))
    
    keyboard.add(*buttons[:5])
    keyboard.add(*buttons[5:10])
    keyboard.add(
        InlineKeyboardButton("🔢 Свой вариант", callback_data=f"guess_custom_{user_id}"),
        InlineKeyboardButton(f"{EMOJI['exit']} Выйти", callback_data=f"guess_exit_{user_id}")
    )
    return keyboard

def back_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"{EMOJI['back']} Назад", callback_data="back_to_menu"))
    return keyboard

def chat_back_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"{EMOJI['back']} Назад в меню", callback_data="back_to_menu"))
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    username = message.from_user.first_name
    welcome_text = f"""✨ Привет, {username}! ✨

Я Юки, аниме-девушка. У меня есть для тебя игры и я могу просто поболтать!

🎮 *Игры:*
• Крестики-нолики
• Камень-ножницы-бумага  
• Угадай число

💬 *Общение:*
• Можешь просто поговорить со мной
• Выбрать режим общения

Выбирай что хочешь делать! :)"""
    
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=main_menu())

# Обработка текстовых сообщений (для угадай числа и чата)
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_message = message.text
    
    if user_message.startswith('/'):
        return
    
    # Проверяем, активна ли игра "Угадай число"
    guess_key = f"guess_{user_id}"
    if guess_key in games_data:
        game = games_data[guess_key]['game']
        if not game.game_over:
            try:
                guess_num = int(user_message.strip())
                if 1 <= guess_num <= 100:
                    success, result = game.guess(guess_num)
                    
                    if success or game.game_over:
                        if success:
                            update_player_stats(user_id, message.from_user.username, 'guess', 'win')
                            result_text = f"🎉 *Победа!*\n\n{result}"
                        else:
                            update_player_stats(user_id, message.from_user.username, 'guess', 'loss')
                            result_text = f"😔 *Поражение*\n\n{result}"
                        
                        bot.send_message(message.chat.id, result_text, parse_mode='Markdown', reply_markup=main_menu())
                        del games_data[guess_key]
                        save_games_data(games_data)
                    else:
                        bot.send_message(message.chat.id, result, parse_mode='Markdown', reply_markup=guess_keyboard(user_id))
                    return
                else:
                    bot.send_message(message.chat.id, "Введи число от 1 до 100!", reply_markup=guess_keyboard(user_id))
                    return
            except ValueError:
                bot.send_message(message.chat.id, "Введи число от 1 до 100!", reply_markup=guess_keyboard(user_id))
                return
    
    # Проверяем, активен ли режим чата
    chat_mode_key = f"chat_mode_{user_id}"
    if chat_mode_key in games_data:
        mode = games_data[chat_mode_key]
        
        if mode == "normal":
            save_chat_message(user_id, "user", user_message)
            
            try:
                bot.send_chat_action(message.chat.id, 'typing')
            except:
                pass
            
            response = get_gpt_response(user_id, user_message)
            
            if response:
                save_chat_message(user_id, "assistant", response)
                bot.send_message(message.chat.id, response, reply_markup=chat_back_menu())
            else:
                bot.send_message(message.chat.id, "Извини, у меня проблемы с интернетом. Давай попробуем еще раз :)", 
                               reply_markup=chat_back_menu())
        else:
            bot.send_message(message.chat.id, "🌸 *Режим в разработке!* 🌸\n\nСкоро здесь будет что-то интересное... А пока можешь выбрать обычный режим общения или поиграть в игры! :)", 
                           parse_mode='Markdown', reply_markup=chat_back_menu())
        return

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    
    try:
        if data == "back_to_menu":
            bot.edit_message_text("✨ Главное меню ✨\n\nВыбери что хочешь сделать:", 
                                call.message.chat.id, call.message.message_id,
                                reply_markup=main_menu())
            
            chat_mode_key = f"chat_mode_{user_id}"
            if chat_mode_key in games_data:
                del games_data[chat_mode_key]
                save_games_data(games_data)
        
        elif data == "my_stats":
            stats_text = get_player_stats(user_id)
            bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id,
                                parse_mode='Markdown', reply_markup=back_menu())
        
        elif data == "global_stats":
            if not players_stats:
                stats_text = "📊 Статистика пока пуста. Сыграй в игры!"
            else:
                total_players = len(players_stats)
                total_games = sum(p['total_games'] for p in players_stats.values())
                total_wins = sum(p['total_wins'] for p in players_stats.values())
                
                top_players = sorted(players_stats.items(), 
                                   key=lambda x: x[1]['total_wins'], reverse=True)[:5]
                
                stats_text = f"🌍 *Глобальная статистика*\n\n"
                stats_text += f"👥 Всего игроков: {total_players}\n"
                stats_text += f"🎮 Всего игр: {total_games}\n"
                stats_text += f"🏆 Всего побед: {total_wins}\n"
                if total_games > 0:
                    stats_text += f"📊 Общий винрейт: {total_wins/total_games*100:.1f}%\n\n"
                
                stats_text += f"⭐ *ТОП-5 ИГРОКОВ* ⭐\n"
                for i, (uid, stats) in enumerate(top_players, 1):
                    winrate = stats['total_wins']/stats['total_games']*100 if stats['total_games'] > 0 else 0
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "•")
                    stats_text += f"{medal} {stats['username']} — {stats['total_wins']} побед ({winrate:.1f}%)\n"
            
            bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id,
                                parse_mode='Markdown', reply_markup=back_menu())
        
        elif data == "game_ttt":
            bot.edit_message_text("🎮 *Крестики-нолики*\n\nВыбери сложность:", 
                                call.message.chat.id, call.message.message_id,
                                parse_mode='Markdown', reply_markup=difficulty_menu())
        
        elif data == "game_rps":
            game = RPS()
            games_data[f"rps_{user_id}"] = {'game': game}
            save_games_data(games_data)
            
            game_text = f"🪨✂️📄 *Камень-ножницы-бумага*\n\nСчет: Ты 0 : 0 Юки\n\nСделай выбор:"
            bot.edit_message_text(game_text, call.message.chat.id, call.message.message_id,
                                parse_mode='Markdown', reply_markup=rps_keyboard(user_id))
        
        elif data == "game_guess":
            game = GuessNumber()
            games_data[f"guess_{user_id}"] = {'game': game}
            save_games_data(games_data)
            
            game_text = f"🔮 *Угадай число*\n\nЯ загадала число от 1 до 100!\nУ тебя 10 попыток ✨\n\nВведи число или используй кнопки:"
            bot.edit_message_text(game_text, call.message.chat.id, call.message.message_id,
                                parse_mode='Markdown', reply_markup=guess_keyboard(user_id))
        
        elif data == "chat_mode":
            bot.edit_message_text("💬 *Общение с Юки*\n\nВыбери режим общения:", 
                                call.message.chat.id, call.message.message_id,
                                parse_mode='Markdown', reply_markup=chat_mode_menu())
        
        elif data == "chat_normal":
            games_data[f"chat_mode_{user_id}"] = "normal"
            save_games_data(games_data)
            
            start_text = """💬 *Обычный режим общения*

Теперь ты можешь просто писать мне, и я буду отвечать как обычная девушка.

Можешь спрашивать о чем угодно, рассказывать о себе или просто болтать.

Напиши что-нибудь! ✨"""
            
            bot.edit_message_text(start_text, call.message.chat.id, call.message.message_id,
                                parse_mode='Markdown', reply_markup=chat_back_menu())
        
        elif data == "chat_lewd":
            lewd_text = """🔥 *Пошлый режим* 🔥

*В разработке!*

Скоро здесь появится что-то интересное... 
А пока можешь использовать обычный режим общения или поиграть в игры! 

Обещаю, будет весело! 😏"""
            
            bot.edit_message_text(lewd_text, call.message.chat.id, call.message.message_id,
                                parse_mode='Markdown', reply_markup=chat_back_menu())
        
        elif data in ["ttt_easy", "ttt_normal", "ttt_hard"]:
            difficulty = data.split('_')[1]
            game = TicTacToe(difficulty)
            games_data[f"ttt_{user_id}"] = {'game': game, 'difficulty': difficulty}
            save_games_data(games_data)
            
            board_text = f"❌⭕ *Крестики-нолики* (Сложность: {difficulty})\n\n{game.get_board_display()}\n\nТвой ход:"
            bot.edit_message_text(board_text, call.message.chat.id, call.message.message_id,
                                parse_mode='Markdown', reply_markup=tic_tac_toe_keyboard(game, user_id))
        
        elif data.startswith("ttt_move_"):
            parts = data.split('_')
            if len(parts) == 4 and parts[2] == str(user_id):
                move = int(parts[3])
                game_key = f"ttt_{user_id}"
                
                if game_key in games_data:
                    game = games_data[game_key]['game']
                    
                    if game.make_move(move):
                        if game.game_over:
                            if game.winner == 'X':
                                result_text = f"🎉 *Победа!*\n\n{game.get_board_display()}\n\nТы выиграл!"
                                update_player_stats(user_id, call.from_user.username, 'ttt', 'win', game.difficulty)
                            elif game.winner == 'O':
                                result_text = f"😔 *Поражение*\n\n{game.get_board_display()}\n\nЯ выиграла..."
                                update_player_stats(user_id, call.from_user.username, 'ttt', 'loss', game.difficulty)
                            else:
                                result_text = f"🤝 *Ничья*\n\n{game.get_board_display()}\n\nНичья!"
                                update_player_stats(user_id, call.from_user.username, 'ttt', 'draw', game.difficulty)
                            
                            bot.edit_message_text(result_text, call.message.chat.id, call.message.message_id,
                                                parse_mode='Markdown', reply_markup=main_menu())
                            del games_data[game_key]
                            save_games_data(games_data)
                        else:
                            game.bot_move()
                            
                            if game.game_over:
                                if game.winner == 'X':
                                    result_text = f"🎉 *Победа!*\n\n{game.get_board_display()}\n\nТы выиграл!"
                                    update_player_stats(user_id, call.from_user.username, 'ttt', 'win', game.difficulty)
                                elif game.winner == 'O':
                                    result_text = f"😔 *Поражение*\n\n{game.get_board_display()}\n\nЯ выиграла..."
                                    update_player_stats(user_id, call.from_user.username, 'ttt', 'loss', game.difficulty)
                                else:
                                    result_text = f"🤝 *Ничья*\n\n{game.get_board_display()}\n\nНичья!"
                                    update_player_stats(user_id, call.from_user.username, 'ttt', 'draw', game.difficulty)
                                
                                bot.edit_message_text(result_text, call.message.chat.id, call.message.message_id,
                                                    parse_mode='Markdown', reply_markup=main_menu())
                                del games_data[game_key]
                                save_games_data(games_data)
                            else:
                                board_text = f"❌⭕ *Крестики-нолики* (Сложность: {game.difficulty})\n\n{game.get_board_display()}\n\nТвой ход:"
                                bot.edit_message_text(board_text, call.message.chat.id, call.message.message_id,
                                                    parse_mode='Markdown', reply_markup=tic_tac_toe_keyboard(game, user_id))
                            save_games_data(games_data)
        
        elif data.startswith("rps_rock_") or data.startswith("rps_scissors_") or data.startswith("rps_paper_"):
            parts = data.split('_')
            if len(parts) == 3 and parts[2] == str(user_id):
                choice_map = {
                    'rock': '🪨',
                    'scissors': '✂️',
                    'paper': '📄'
                }
                player_choice = choice_map[parts[1]]
                game_key = f"rps_{user_id}"
                
                if game_key in games_data:
                    game = games_data[game_key]['game']
                    result, bot_choice, winner = game.play(player_choice)
                    
                    update_text = f"🪨✂️📄 *Камень-ножницы-бумага*\n\n"
                    update_text += f"Твой выбор: {player_choice} {game.choices[player_choice]}\n"
                    update_text += f"Мой выбор: {bot_choice} {game.choices[bot_choice]}\n\n"
                    update_text += f"{result}\n\n"
                    update_text += f"📊 Счет: Ты {game.player_score} : {game.bot_score} Я\n"
                    update_text += f"🎲 Раунд: {game.rounds}\n\n"
                    
                    if winner == 'draw':
                        stats_result = 'draw'
                    elif winner == 'player':
                        stats_result = 'win'
                    else:
                        stats_result = 'loss'
                    
                    update_player_stats(user_id, call.from_user.username, 'rps', stats_result)
                    
                    update_text += "Сделай следующий выбор:"
                    bot.edit_message_text(update_text, call.message.chat.id, call.message.message_id,
                                        parse_mode='Markdown', reply_markup=rps_keyboard(user_id))
                    save_games_data(games_data)
        
        elif data.startswith("guess_num_"):
            parts = data.split('_')
            if len(parts) == 4 and parts[2] == str(user_id):
                guess_num = int(parts[3])
                game_key = f"guess_{user_id}"
                
                if game_key in games_data:
                    game = games_data[game_key]['game']
                    success, result = game.guess(guess_num)
                    
                    if success or game.game_over:
                        if success:
                            update_player_stats(user_id, call.from_user.username, 'guess', 'win')
                            result_text = f"🎉 *Победа!*\n\n{result}"
                        else:
                            update_player_stats(user_id, call.from_user.username, 'guess', 'loss')
                            result_text = f"😔 *Поражение*\n\n{result}"
                        
                        bot.edit_message_text(result_text, call.message.chat.id, call.message.message_id,
                                            parse_mode='Markdown', reply_markup=main_menu())
                        del games_data[game_key]
                        save_games_data(games_data)
                    else:
                        bot.edit_message_text(result, call.message.chat.id, call.message.message_id,
                                            parse_mode='Markdown', reply_markup=guess_keyboard(user_id))
        
        elif data.startswith("guess_custom_"):
            parts = data.split('_')
            if len(parts) == 3 and parts[2] == str(user_id):
                bot.edit_message_text("🔢 Введи число от 1 до 100:", 
                                    call.message.chat.id, call.message.message_id,
                                    reply_markup=guess_keyboard(user_id))
        
        elif data.startswith("ttt_exit_"):
            parts = data.split('_')
            if len(parts) == 3 and parts[2] == str(user_id):
                game_key = f"ttt_{user_id}"
                if game_key in games_data:
                    del games_data[game_key]
                    save_games_data(games_data)
                bot.edit_message_text("🚪 Игра завершена. Возвращаюсь в меню...", 
                                    call.message.chat.id, call.message.message_id,
                                    reply_markup=main_menu())
        
        elif data.startswith("rps_exit_"):
            parts = data.split('_')
            if len(parts) == 3 and parts[2] == str(user_id):
                game_key = f"rps_{user_id}"
                if game_key in games_data:
                    del games_data[game_key]
                    save_games_data(games_data)
                bot.edit_message_text("🚪 Игра завершена. Возвращаюсь в меню...", 
                                    call.message.chat.id, call.message.message_id,
                                    reply_markup=main_menu())
        
        elif data.startswith("guess_exit_"):
            parts = data.split('_')
            if len(parts) == 3 and parts[2] == str(user_id):
                game_key = f"guess_{user_id}"
                if game_key in games_data:
                    del games_data[game_key]
                    save_games_data(games_data)
                bot.edit_message_text("🚪 Игра завершена. Возвращаюсь в меню...", 
                                    call.message.chat.id, call.message.message_id,
                                    reply_markup=main_menu())
        
        bot.answer_callback_query(call.id)
    
    except Exception as e:
        print(f"Ошибка: {e}")

def run_bot():
    while True:
        try:
            print("🌸 Юки запущена!")
            print("🎮 Игры и общение в одном боте")
            print("💬 Готова к работе")
            print("")
            bot.remove_webhook()
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

if __name__ == '__main__':
    run_bot()
