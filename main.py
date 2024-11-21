import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler

# Этапы разговора для управления состоянием
ASK_PASSWORD, ADMIN_PANEL, ADD_MUSIC, DELETE_MUSIC, CONFIRM_DELETE = range(5)

# Файл для хранения информации о загруженной музыке
MUSIC_STORAGE_FILE = "music_storage.json"

# Директория для хранения музыкальных файлов
MUSIC_DIR = "music_files"

# Пароль для админки
PASSWORD = "240405"

# Количество треков на одной странице при удалении
PAGE_SIZE = 3

# Создаем директорию для хранения файлов, если она не существует
if not os.path.exists(MUSIC_DIR):
    os.makedirs(MUSIC_DIR)

# Загружаем информацию о музыке из файла (если файл существует)
if os.path.exists(MUSIC_STORAGE_FILE):
    with open(MUSIC_STORAGE_FILE, 'r', encoding='utf-8') as f:
        music_storage = json.load(f)
else:
    music_storage = {}

# Сохранение данных о музыке в файл
def save_music_storage():
    with open(MUSIC_STORAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(music_storage, f, ensure_ascii=False, indent=4)

# Главное меню с корректным завершением диалога
async def start(update: Update, context):
    reply_keyboard = [['Админ панель']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text('Привет! Что хочешь сделать?', reply_markup=markup)
    return ConversationHandler.END  # Завершаем диалог здесь после возврата в главное меню

# Запрашиваем пароль у пользователя для входа в админ панель
async def ask_password(update: Update, context):
    reply_keyboard = [['Назад']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        'Для доступа к админ панели введите пароль или нажмите "Назад" для возврата в главное меню.',
        reply_markup=markup)
    return ASK_PASSWORD

# Проверка пароля
async def check_password(update: Update, context):
    if update.message.text == "Назад":
        await start(update, context)
        return ConversationHandler.END  # Завершаем диалог

    if update.message.text == PASSWORD:
        reply_keyboard = [['Добавить трек', 'Удалить трек', 'Назад']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text('Пароль верный. Выберите действие:', reply_markup=markup)
        return ADMIN_PANEL
    else:
        reply_keyboard = [['Назад']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            'Неверный пароль. Попробуйте еще раз или нажмите "Назад" для возврата в главное меню.', reply_markup=markup)
        return ASK_PASSWORD

# Обработка добавления музыки
async def handle_music(update: Update, context):
    if update.message.text == "Назад":
        reply_keyboard = [['Добавить трек', 'Удалить трек', 'Назад']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text('Вы вернулись в админ панель. Выберите действие:', reply_markup=markup)
        return ADMIN_PANEL

    # Проверяем, что пользователь прислал файл
    if update.message.audio or update.message.document:
        file = update.message.audio or update.message.document
        comment = update.message.caption if update.message.caption else "Без комментария"

        # Скачиваем файл на локальный диск
        file_id = file.file_id
        file_name = file.file_name
        new_file = await context.bot.get_file(file_id)
        file_path = os.path.join(MUSIC_DIR, file_name)
        await new_file.download_to_drive(file_path)

        # Сохраняем информацию о файле
        music_storage[file_id] = {
            "file_path": file_path,
            "comment": comment,
            "file_name": file_name
        }

        # Сохраняем обновленный словарь в файл
        save_music_storage()

        # Отправляем сообщение об успешном добавлении трека
        await update.message.reply_text(f'Файл "{file_name}" успешно загружен с комментарием: {comment}')

        # Возвращаемся в админ панель
        reply_keyboard = [['Добавить трек', 'Удалить трек', 'Назад']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text('Вы вернулись в админ панель. Выберите действие:', reply_markup=markup)
        return ADMIN_PANEL
    else:
        await update.message.reply_text(
            'Пожалуйста, загрузите аудиофайл или нажмите "Назад" для возврата в админ панель.')
        return ADD_MUSIC

# Показываем список треков с листанием
async def delete_track(update: Update, context):
    context.user_data['page'] = 0  # Начинаем с первой страницы
    return await show_tracks(update, context)

# Отображение треков на указанной странице
async def show_tracks(update: Update, context):
    page = context.user_data.get('page', 0)
    tracks = list(music_storage.keys())
    total_tracks = len(tracks)

    if total_tracks == 0:
        await update.message.reply_text("Нет доступных треков для удаления.")
        return ADMIN_PANEL

    start_idx = page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_tracks)

    # Формируем кнопки для треков на текущей странице
    reply_keyboard = [[f"Трек {i + 1}" for i in range(start_idx, end_idx)]]

    # Добавляем кнопки для листания
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append("<-----")
    if end_idx < total_tracks:
        navigation_buttons.append("----->")

    if navigation_buttons:
        reply_keyboard.append(navigation_buttons)

    # Кнопка возврата
    reply_keyboard.append(["Назад"])

    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите трек для удаления или используйте кнопки для навигации.",
                                    reply_markup=markup)

    return DELETE_MUSIC

# Обработка выбора трека для удаления
async def select_track_for_delete(update: Update, context):
    text = update.message.text
    if text == "Назад":
        return await general_admin_panel(update, context)

    if text == "----->":
        context.user_data['page'] += 1
        return await show_tracks(update, context)
    elif text == "<-----":
        context.user_data['page'] -= 1
        return await show_tracks(update, context)

    # Проверяем, что выбран трек
    try:
        track_num = int(text.split()[1]) - 1  # Получаем индекс трека
        track_id = list(music_storage.keys())[track_num]
        context.user_data['track_to_delete'] = track_id  # Сохраняем трек для удаления

        reply_keyboard = [['Да', 'Нет']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            f"Вы уверены, что хотите удалить трек {track_num + 1}? Это действие нельзя отменить.", reply_markup=markup)

        return CONFIRM_DELETE
    except (IndexError, ValueError):
        await update.message.reply_text("Некорректный выбор. Пожалуйста, выберите трек из списка.")
        return await show_tracks(update, context)

# Подтверждение удаления трека
async def confirm_delete_track(update: Update, context):
    if update.message.text == "Да":
        track_id = context.user_data.get('track_to_delete')

        if track_id in music_storage:
            # Удаляем файл с диска
            try:
                os.remove(music_storage[track_id]['file_path'])
            except OSError as e:
                await update.message.reply_text(f"Ошибка при удалении файла: {e}")

            # Удаляем информацию о треке
            del music_storage[track_id]
            save_music_storage()

            await update.message.reply_text("Трек успешно удален.")
        else:
            await update.message.reply_text("Трек не найден.")

    return await show_tracks(update, context)

## Общая панель администратора
async def general_admin_panel(update: Update, context):
    reply_keyboard = [['Добавить трек', 'Удалить трек', 'Назад']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text('Вы вернулись в админ панель. Выберите действие:', reply_markup=markup)
    return ADMIN_PANEL

if __name__ == '__main__':
    # Создаем приложение
    application = ApplicationBuilder().token("7828768545:AAG08qKjmZyoY6cqI5rZXdNTyVy-szCuf50").build()

    # Создаем ConversationHandler для обработки диалога
    admin_panel_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("Админ панель"), ask_password)],
        states={
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
            ADMIN_PANEL: [
                MessageHandler(filters.Text("Добавить трек"), handle_music),
                MessageHandler(filters.Text("Удалить трек"), delete_track),
                MessageHandler(filters.Text("Назад"), start)
            ],
            ADD_MUSIC: [MessageHandler(filters.AUDIO | filters.Document.ALL | filters.Text("Назад"), handle_music)],
            DELETE_MUSIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_track_for_delete)],
            CONFIRM_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete_track)],
        },
        fallbacks=[]
    )

    # Регистрация обработчиков команд и сообщений
    application.add_handler(CommandHandler('start', start))
    application.add_handler(admin_panel_handler)

    # Запускаем бота
    application.run_polling()