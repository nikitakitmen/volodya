import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.error import Forbidden

# Подгружаем хранилище музыки и директорию, где хранятся файлы
MUSIC_STORAGE_FILE = "music_storage.json"
MUSIC_DIR = "music_files"
CHAT_STORAGE_FILE = "chat_storage.json"

# Проверяем, существует ли файл с музыкой и чатов
if os.path.exists(MUSIC_STORAGE_FILE):
    with open(MUSIC_STORAGE_FILE, 'r', encoding='utf-8') as f:
        music_storage = json.load(f)
else:
    music_storage = {}

if os.path.exists(CHAT_STORAGE_FILE):
    with open(CHAT_STORAGE_FILE, 'r', encoding='utf-8') as f:
        chat_storage = json.load(f)
else:
    chat_storage = []

# Состояние для управления процессом оценки треков и добавления комментариев
USER_STATE = {}


# Обработчик команды /start
async def start(update: Update, context: CallbackContext):
    # Создаем клавиатуру с кнопкой "Прослушать музыку"
    reply_keyboard = [['▶️ Послушать музыки красивой ']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

    # Отправляем сообщение с клавиатурой
    await update.message.reply_text('👋🏻👋🏻, Выбери действие!', reply_markup=markup)


# Функция для отправки всех треков сразу
async def listen_music(update: Update, context: CallbackContext):
    # Перед отправкой треков перечитываем актуальные данные из файла
    if os.path.exists(MUSIC_STORAGE_FILE):
        with open(MUSIC_STORAGE_FILE, 'r', encoding='utf-8') as f:
            music_storage = json.load(f)
    else:
        music_storage = {}

    if not music_storage:
        await update.message.reply_text("Треки пока не загружены.")
        return

    for i, track_id in enumerate(music_storage.keys(), start=1):
        track = music_storage[track_id]
        file_path = track["file_path"]
        comment = track["comment"]

        # Проверяем, существует ли файл
        if not os.path.exists(file_path):
            await update.message.reply_text(f"Файл для трека №{i} не найден: {file_path}")
            continue  # Пропускаем этот трек, если файл отсутствует

        # Отправляем трек с его номером и комментарием
        with open(file_path, 'rb') as audio_file:
            await context.bot.send_audio(
                chat_id=update.message.chat_id,
                audio=audio_file,
                caption=f"Трек №{i}: {comment}"
            )

    # Добавляем кнопки "Поставить оценку" и "Назад"
    reply_keyboard = [['Поставить оценку', 'Назад']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text('Выберите действие:', reply_markup=markup)


# Функция для возврата в главное меню
async def go_back(update: Update, context: CallbackContext):
    await start(update, context)


# Функция для начала оценки треков
async def rate_music(update: Update, context: CallbackContext):
    # Обновляем данные из файла перед каждым вызовом
    if os.path.exists(MUSIC_STORAGE_FILE):
        with open(MUSIC_STORAGE_FILE, 'r', encoding='utf-8') as f:
            music_storage = json.load(f)
    else:
        music_storage = {}

    if not music_storage:
        await update.message.reply_text("Треки пока не загружены.")
        return

    # Получаем список треков
    track_names = list(music_storage.keys())
    total_tracks = len(track_names)
    page = context.user_data.get('page', 0)  # Текущая страница (по умолчанию 0)

    # Определяем начало и конец страницы
    start_idx = page * 3
    end_idx = min(start_idx + 3, total_tracks)

    # Формируем список треков на текущей странице (в одну строку)
    reply_keyboard = []
    tracks_on_page = [f"Трек {i + 1}" for i in range(start_idx, end_idx)]
    if tracks_on_page:
        reply_keyboard.append(tracks_on_page)  # Добавляем треки на одну строку

    # Добавляем кнопки для навигации
    navigation_buttons = []

    # Добавляем кнопку влево только если это не первая страница
    if page > 0:
        navigation_buttons.append("<-----")

    # Добавляем кнопку вправо только если это не последняя страница
    if end_idx < total_tracks:
        navigation_buttons.append("----->")

    # Если есть кнопки для навигации, добавляем их в клавиатуру
    if navigation_buttons:
        reply_keyboard.append(navigation_buttons)

    # Кнопка возврата
    reply_keyboard.append(["Назад"])

    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text('Выберите трек для оценки:', reply_markup=markup)



# Обработка нажатий на кнопки для листания страниц
async def navigate_tracks(update: Update, context: CallbackContext):
    user_text = update.message.text

    # Обрабатываем нажатие на стрелки
    if user_text == "----->":
        context.user_data['page'] = context.user_data.get('page', 0) + 1
    elif user_text == "<-----":
        context.user_data['page'] = context.user_data.get('page', 0) - 1

    # Возвращаемся к выбору треков с обновленной страницей
    await rate_music(update, context)

# Обработка выбора трека для оценки
async def rate_track(update: Update, context: CallbackContext):
    user_text = update.message.text

    if os.path.exists(MUSIC_STORAGE_FILE):
        with open(MUSIC_STORAGE_FILE, 'r', encoding='utf-8') as f:
            music_storage = json.load(f)
    else:
        music_storage = {}

    if user_text.startswith("Трек"):
        try:
            track_num = int(user_text.split()[1])
        except (IndexError, ValueError):
            await update.message.reply_text("Пожалуйста, выберите трек в формате 'Трек <номер>'!")
            return

        if track_num > len(music_storage):
            await update.message.reply_text("Трек с таким номером не найден.")
            return

        track_id = list(music_storage.keys())[track_num - 1]
        context.user_data['track_id'] = track_id
        context.user_data['state'] = 'rating'

        reply_keyboard = [['⭐️', '⭐️⭐️', '⭐️⭐️⭐️'], ['⭐️⭐️⭐️⭐️', '⭐️⭐️⭐️⭐️⭐️'], ['Назад']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(f'Оцените трек №{track_num} от 1 до 5 звёзд:', reply_markup=markup)

    elif user_text in ['⭐️', '⭐️⭐️', '⭐️⭐️⭐️', '⭐️⭐️⭐️⭐️', '⭐️⭐️⭐️⭐️⭐️']:
        rating = user_text.count('⭐️')
        track_id = context.user_data.get('track_id')

        if track_id:
            music_storage[track_id]['rating'] = rating

            with open(MUSIC_STORAGE_FILE, 'w', encoding='utf-8') as f:
                json.dump(music_storage, f, ensure_ascii=False, indent=4)

            context.user_data['state'] = 'bit_question'

            reply_keyboard = [
                ['▶️ мне не понравился (г0_овно)'],
                ['▶️ ну норм, нормис, да'],
                ['▶️ круто, лайк!']
            ]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text('Как тебе бит?', reply_markup=markup)

    elif context.user_data.get('state') == 'bit_question':
        context.user_data['bit_feedback'] = user_text
        context.user_data['state'] = 'text_question'

        reply_keyboard = [
            ['▶️ а в чем смысл? 0_о'],
            ['▶️ да пойдет, да, норм'],
            ['▶️ круто, лайк!']
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text('Как тебе текст? Ты же тоже чувствуешь эту глубину?)', reply_markup=markup)

    elif context.user_data.get('state') == 'text_question':
        context.user_data['text_feedback'] = user_text
        context.user_data['state'] = 'comment'

        await update.message.reply_text('Теперь оставьте комментарий.')

    elif context.user_data.get('state') == 'comment':
        track_id = context.user_data.get('track_id')
        bit_feedback = context.user_data.get('bit_feedback')
        text_feedback = context.user_data.get('text_feedback')
        comment = user_text

        if track_id:
            music_storage[track_id]['user_comment'] = comment

            with open(MUSIC_STORAGE_FILE, 'w', encoding='utf-8') as f:
                json.dump(music_storage, f, ensure_ascii=False, indent=4)

            track_num = list(music_storage.keys()).index(track_id) + 1
            track_comment = music_storage[track_id]["comment"]
            rating = music_storage[track_id].get("rating", "Нет оценки")

            message_text = (
                f"Трек №{track_num}: {track_comment}\n"
                f"Оценка: {'⭐️' * rating}\n"
                f"Бит: {bit_feedback}\n"
                f"Текст: {text_feedback}\n"
                f"Комментарий: {comment}"
            )

            if 'file_id' not in music_storage[track_id]:
                with open(music_storage[track_id]['file_path'], 'rb') as audio_file:
                    audio_message = await context.bot.send_audio(
                        chat_id=update.message.chat_id,
                        audio=audio_file,
                        caption=message_text
                    )
                    music_storage[track_id]['file_id'] = audio_message.audio.file_id

                    with open(MUSIC_STORAGE_FILE, 'w', encoding='utf-8') as f:
                        json.dump(music_storage, f, ensure_ascii=False, indent=4)

            for chat_id in chat_storage:
                if chat_id != update.message.chat_id:
                    try:
                        if 'file_id' in music_storage[track_id]:
                            await context.bot.send_audio(
                                chat_id=chat_id,
                                audio=music_storage[track_id]['file_id'],
                                caption=message_text
                            )
                        else:
                            with open(music_storage[track_id]['file_path'], 'rb') as audio_file:
                                await context.bot.send_audio(
                                    chat_id=chat_id,
                                    audio=audio_file,
                                    caption=message_text
                                )
                    except Forbidden:
                        chat_storage.remove(chat_id)
                        with open(CHAT_STORAGE_FILE, 'w', encoding='utf-8') as f:
                            json.dump(chat_storage, f, ensure_ascii=False, indent=4)
                        print(f"Чат {chat_id} был удален, убираем его из списка.")

            await rate_music(update, context)

    elif user_text == "Назад":
        await go_back(update, context)


# Функция для обработки добавления бота в новый чат
async def bot_added_to_chat(update: Update, context: CallbackContext):
    for member in update.message.new_chat_members:
        # Проверяем, является ли новый участник самим ботом
        if member.id == context.bot.id:
            chat_id = update.message.chat_id

            # Если чат не в списке, добавляем его
            if chat_id not in chat_storage:
                chat_storage.append(chat_id)

                # Обновляем файл с чатами
                with open(CHAT_STORAGE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(chat_storage, f, ensure_ascii=False, indent=4)

            # Бот добавлен в новый чат, отправляем сообщение
            await context.bot.send_message(
                chat_id=chat_id,
                text="Бот успешно добавлен в этот чат!"
            )
            break


# Основная функция
if __name__ == '__main__':
    # Создаем приложение
    application = ApplicationBuilder().token("7950692870:AAF5GO3u6cXmDaTMKyOavobZwxckCTPzBwc").build()

    # Регистрируем обработчик команды /start
    application.add_handler(CommandHandler('start', start))

    # Регистрация обработки кнопки "Прослушать музыку"
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^▶️ Послушать музыки красивой$"), listen_music))

    # Регистрация обработки кнопки "Поставить оценку"
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Поставить оценку$"), rate_music))

    # Обработка кнопки "Назад"
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Назад$"), go_back))

    # Обработка кнопок для навигации треков
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(<-----|----->)$"), navigate_tracks))

    # Обработка выбора трека и оценки
    application.add_handler(MessageHandler(filters.TEXT, rate_track))

    # Обработка добавления бота в чат
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_added_to_chat))

    # Запускаем бота
    application.run_polling()
