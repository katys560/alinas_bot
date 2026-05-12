import asyncio
import logging
import random
import aiosqlite
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)

TOKEN = '8359750583:AAGPVmC7XdslBhBKO28DblZQb1lHoQTN0tA'
DB_PATH = 'army_bot.db'
SERVICE_MONTHS = 12

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot = Bot(token=TOKEN)
scheduler = AsyncIOScheduler()


# ─── FSM ────────────────────────────────────────────────────────────────────

class Registration(StatesGroup):
    name = State()
    call_date = State()
    unit = State()


# ─── Keyboard ───────────────────────────────────────────────────────────────

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏱ Таймер"), KeyboardButton(text="📊 % службы")],
            [KeyboardButton(text="⭐ Русская рулетка"), KeyboardButton(text="💟 Профиль")],
        ],
        resize_keyboard=True,
    )


# ─── Database ───────────────────────────────────────────────────────────────

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id    INTEGER PRIMARY KEY,
                name       TEXT NOT NULL,
                call_date  TEXT NOT NULL,
                unit       TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cur:
            return await cur.fetchone()


async def save_user(user_id: int, name: str, call_date: str, unit: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR REPLACE INTO users (user_id, name, call_date, unit) VALUES (?, ?, ?, ?)',
            (user_id, name, call_date, unit),
        )
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users') as cur:
            return await cur.fetchall()


# ─── Service calculations ────────────────────────────────────────────────────

def calc_service(call_date_str: str) -> dict:
    call = datetime.strptime(call_date_str, '%d.%m.%Y')
    demob = call + relativedelta(months=SERVICE_MONTHS)
    now = datetime.now()

    passed_days = max(0, (now - call).days)
    passed_weeks = passed_days // 7
    passed_delta = relativedelta(now, call)
    passed_months = max(0, passed_delta.years * 12 + passed_delta.months)

    remaining_days = max(0, (demob - now).days)
    remaining_weeks = remaining_days // 7
    rem_delta = relativedelta(demob, now)
    remaining_months = max(0, rem_delta.years * 12 + rem_delta.months)

    total_days = (demob - call).days
    percentage = max(0.0, min(100.0, passed_days / total_days * 100))

    return {
        'passed_months': passed_months,
        'passed_weeks': passed_weeks,
        'passed_days': passed_days,
        'remaining_months': remaining_months,
        'remaining_weeks': remaining_weeks,
        'remaining_days': remaining_days,
        'percentage': percentage,
        'demob': demob,
    }


# ─── Orders ─────────────────────────────────────────────────────────────────

ORDERS = [
    "Копать отсюда и до дембеля!",
    "Покрасить снег в зимний камуфляж!",
    "Пересчитать все звёзды на погонах у генералов!",
    "Найти Wi-Fi в лесу и доложить пароль!",
    "Поймать голубя-шпиона!",
    "Построить взвод по знаку зодиака!",
    "Отжаться за всю роту!",
    "Принести воздух со склада!",
    "Подмести плац зубной щёткой!",
    "Разбудить прапорщика раньше будильника!",
    "Выровнять сугробы по уставу!",
    "Проверить, ровно ли светит солнце!",
    "Замаскировать чайник под БТР!",
    "Собрать комаров в одну шеренгу!",
    "Протереть пыль на облаках!",
    "Организовать охрану тумбочки!",
    "Срочно найти виновного!",
    "Построить тараканов на вечернюю поверку!",
    "Найти конец армейского скотча!",
    "Сделать селфи с дежурным по части!",
    "Натянуть одеяло по нитке!",
    "Принять участие в чемпионате по чистке картошки!",
    "Доложить обстановку на кухне!",
    "Отправиться в секретную миссию за хлебом!",
    "Проверить наличие воды в кулере методом дегустации!",
    "Убедиться, что трава растёт по уставу!",
    "Выдать каждому комару увольнительную!",
    "Собрать все окурки по алфавиту!",
    "Отполировать лопату до блеска!",
    "Найти смысл службы в наряде!",
    "Проверить, не убежал ли плац!",
    "Организовать банный день для сапог!",
    "Подготовить доклад о стратегическом значении тушёнки!",
    "Обеспечить связь с инопланетянами!",
    "Перемыть кубрик взглядом!",
    "Построить роту по размеру берцев!",
    "Убедиться, что чай достаточно армейский!",
    "Проверить, одинаково ли храпят сослуживцы!",
    "Поймать муху нарушителя!",
    "Выяснить, кто съел сгущёнку!",
    "Провести инвентаризацию носков!",
    "Организовать доставку сна личному составу!",
    "Сделать подворотничок уровня спецназа!",
    "Проверить горизонтальность кроватей!",
    "Прочитать устав комарам перед сном!",
    "Подготовить плац к визиту Марса!",
    "Найти добровольца для наряда!",
    "Проверить моральное состояние чайника!",
    "Добыть кипяток без чайника!",
    "Сделать кантик идеальной формы!",
    "Построить очередь в туалет по уставу!",
    "Проверить скорость высыхания портянок!",
    "Провести разведку холодильника!",
    "Поймать нарушителя отбоя!",
    "Сдать норматив по лежанию на кровати!",
    "Организовать марш-бросок до столовой!",
    "Секретно охранять печенье!",
    "Почистить картошку тактически!",
    "Подготовить сапоги к параду!",
    "Найти крайнего в роте!",
    "Подмести листья зимой!",
    "Согласовать дождь с командованием!",
    "Проверить боеготовность кружек!",
    "Подготовить табурет к инспекции!",
    "Перекрасить ржавчину в цвет устава!",
    "Принести справку о наличии справки!",
    "Проверить уровень суровости прапорщика!",
    "Выпрямить матрас силой мысли!",
    "Замаскировать следы после кухни!",
    "Сделать генеральную уборку пылинки!",
    "Подготовить отчёт о потерях носков!",
    "Найти того, кто не устал!",
    "Проверить устойчивость табуретки!",
    "Срочно доставить чай в штаб!",
    "Подшить воротничок с закрытыми глазами!",
    "Организовать стратегический запас сахара!",
    "Собрать все крошки в кубрике!",
    "Проверить исправность швабры!",
    "Сделать лицо бодрым к подъёму!",
    "Сдать норматив по быстрому одеванию!",
    "Провести учения по спасению тапка!",
    "Организовать оборону от комаров!",
    "Проверить, не закончился ли воздух!",
    "Подготовить доклад о состоянии тапочек!",
    "Поймать сон до отбоя!",
    "Проверить уровень квадратности сугробов!",
    "Принести невидимую папку!",
    "Построить взвод по любимой каше!",
    "Убедиться, что подушка заправлена!",
    "Проверить боевой дух веников!",
    "Организовать караул у холодильника!",
    "Найти ответственного за понедельник!",
    "Проверить, не расслабился ли личный состав!",
    "Провести операцию 'Тихий чайник'!",
    "Подмести плац от снега во время снегопада!",
    "Проверить стратегический запас туалетной бумаги!",
    "Поймать тень нарушителя!",
    "Сделать кровать по линейке!",
    "Сдать экзамен по стоянию в строю!",
    "Принести левый ботинок от правой пары!",
    "Подготовить доклад о поведении мух!",
    "Обеспечить идеальную тишину храпящих!",
    "Проверить наличие мотивации у швабры!",
    "Найти секретный вход в столовую!",
    "Провести спецоперацию по добыче чая!",
]


# ─── Reminders ──────────────────────────────────────────────────────────────

async def send_reminder(user_id: int, text: str):
    try:
        await bot.send_message(user_id, text)
    except Exception as e:
        logging.error(f"Reminder error for {user_id}: {e}")


def schedule_user_reminders(user_id: int, call_date_str: str):
    call = datetime.strptime(call_date_str, '%d.%m.%Y')
    demob = call + relativedelta(months=SERVICE_MONTHS)
    now = datetime.now()

    # Every 28 days (≈ 1 month)
    month_num = 1
    while True:
        run_at = call + timedelta(days=28 * month_num)
        if run_at > demob:
            break
        if run_at > now:
            scheduler.add_job(
                send_reminder, 'date', run_date=run_at,
                args=[user_id, f"⏰ Прошёл {month_num} мес. службы!"],
                id=f"28d_{user_id}_{month_num}", replace_existing=True,
            )
        month_num += 1

    # 6 months
    half = call + relativedelta(months=6)
    if half > now:
        scheduler.add_job(
            send_reminder, 'date', run_date=half,
            args=[user_id, "🎉 Полгода службы позади! Ты на середине пути! 🪖"],
            id=f"half_{user_id}", replace_existing=True,
        )

    # Day before demob
    eve = demob - timedelta(days=1)
    if eve > now:
        scheduler.add_job(
            send_reminder, 'date', run_date=eve,
            args=[user_id, "🎊 Завтра ДЕМБЕЛЬ! Готовь чемодан! 🎊"],
            id=f"demob_{user_id}", replace_existing=True,
        )


# ─── Handlers ───────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if user:
        await message.answer(f"С возвращением, {user['name']}! 🫡", reply_markup=main_kb())
    else:
        await state.set_state(Registration.name)
        await message.answer(f'Добро пожаловать!{message.from_user.username} Давай создадим твой профиль.\n\nКак мне записать тебя?')


@dp.message(StateFilter(Registration.name))
async def reg_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Registration.call_date)
    await message.answer("💘Введи дату призыва в формате ДД.ММ.ГГГГ\n(например: 15.11.2024):")


@dp.message(StateFilter(Registration.call_date))
async def reg_call_date(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text, '%d.%m.%Y')
    except ValueError:
        await message.answer("Неверный формат дура. Введи дату в виде ДД.ММ.ГГГГ:")
        return
    await state.update_data(call_date=message.text)
    await state.set_state(Registration.unit)
    await message.answer("Введи название воинской части:")


@dp.message(StateFilter(Registration.unit))
async def reg_unit(message: Message, state: FSMContext):
    data = await state.get_data()
    await save_user(message.from_user.id, data['name'], data['call_date'], message.text)
    await state.clear()

    info = calc_service(data['call_date'])
    schedule_user_reminders(message.from_user.id, data['call_date'])

    await message.answer(
        f"✅ <b>Профиль создан!</b>\n\n"
        f"🪖 Имя: {data['name']}\n"
        f"📅 Призыв: {data['call_date']}\n"
        f"🏠 Часть: {message.text}\n"
        f"🏁 Дембель: <b>{info['demob'].strftime('%d.%m.%Y')}</b>",
        parse_mode='HTML',
        reply_markup=main_kb(),
    )


def timer_inline_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Месяца",  callback_data="timer_months"),
            InlineKeyboardButton(text="📆 Недели",  callback_data="timer_weeks"),
            InlineKeyboardButton(text="🗓 Дни",     callback_data="timer_days"),
        ]
    ])


def make_bar(pct: float, size: int = 10) -> str:
    filled = round(pct / 100 * size)
    passed_bar   = '🟩' * filled + '⬜' * (size - filled)
    remaining_bar = '🟥' * (size - filled) + '⬜' * filled
    return f"✅ {passed_bar}\n⏳ {remaining_bar}"


@dp.message(F.text == "⏱ Таймер")
async def timer_handler(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйся — /start")
        return

    i = calc_service(user['call_date'])
    await message.answer(
        f"⏱ <b>Таймер службы</b>\n\n"
        f"✅ <b>Прошло:</b>\n"
        f"  • {i['passed_months']} мес. | {i['passed_weeks']} нед. | {i['passed_days']} дн.\n\n"
        f"⏳ <b>Осталось:</b>\n"
        f"  • {i['remaining_months']} мес. | {i['remaining_weeks']} нед. | {i['remaining_days']} дн.\n\n"
        f"🏁 Дата дембеля: <b>{i['demob'].strftime('%d.%m.%Y')}</b>\n\n"
        f"Выбери:",
        parse_mode='HTML',
        reply_markup=timer_inline_kb(),
    )


@dp.callback_query(F.data == "timer_months")
async def cb_timer_months(callback: CallbackQuery):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    if not user:
        return
    i = calc_service(user['call_date'])
    total_months = SERVICE_MONTHS
    pct = i['percentage']
    await callback.message.answer(
        f"📅 <b>Месяца</b>\n\n"
        f"{make_bar(pct)}\n"
        f"✅ Прошло:   <b>{i['passed_months']} из {total_months} мес.</b>\n"
        f"⏳ Осталось: <b>{i['remaining_months']} мес.</b>",
        parse_mode='HTML',
    )


@dp.callback_query(F.data == "timer_weeks")
async def cb_timer_weeks(callback: CallbackQuery):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    if not user:
        return
    i = calc_service(user['call_date'])
    total_weeks = SERVICE_MONTHS * 4
    pct = i['percentage']
    await callback.message.answer(
        f"📆 <b>Недели</b>\n\n"
        f"{make_bar(pct)}\n"
        f"✅ Прошло:   <b>{i['passed_weeks']} нед.</b>\n"
        f"⏳ Осталось: <b>{i['remaining_weeks']} из ~{total_weeks} нед.</b>",
        parse_mode='HTML',
    )


@dp.callback_query(F.data == "timer_days")
async def cb_timer_days(callback: CallbackQuery):
    await callback.answer()
    user = await get_user(callback.from_user.id)
    if not user:
        return
    i = calc_service(user['call_date'])
    total_days = SERVICE_MONTHS * 30
    pct = i['percentage']
    await callback.message.answer(
        f"🗓 <b>Дни</b>\n\n"
        f"{make_bar(pct)}\n"
        f"✅ Прошло:   <b>{i['passed_days']} дн.</b>\n"
        f"⏳ Осталось: <b>{i['remaining_days']} из ~{total_days} дн.</b>",
        parse_mode='HTML',
    )


@dp.message(F.text == "📊 % службы")
async def percent_handler(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйся — /start")
        return

    i = calc_service(user['call_date'])
    pct = i['percentage']

    if pct < 30:
        medal = '🥉'
    elif pct < 60:
        medal = '🥈'
    elif pct < 90:
        medal = '🥇'
    else:
        medal = '🏆'

    bar = make_bar(pct, size=12)

    await message.answer(
        f"📊 <b>Прогресс службы</b>\n\n"
        f"{bar}\n\n"
        f"{medal} <b>{pct:.1f}%</b> пройдено\n\n"
        f"✅ Прошло:   <b>{i['passed_days']} дн.</b>\n"
        f"⏳ Осталось: <b>{i['remaining_days']} дн.</b>\n\n"
        f"🏁 Дата дембеля: <b>{i['demob'].strftime('%d.%m.%Y')}</b>",
        parse_mode='HTML',
    )


@dp.message(F.text == "⭐ Русская рулетка")
async def roulette_handler(message: Message):
    order = random.choice(ORDERS)
    await message.answer(
        f"🎲 <b>Приказ дня:</b>\n\n"
        f"«{order}»\n\n"
        f"<i>Выполнять немедленно! 🫡</i>",
        parse_mode='HTML',
    )


def edit_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❔ Редактировать", callback_data="edit_profile")]
    ])


@dp.message(F.text == "💟 Профиль")
async def profile_handler(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйся — /start")
        return

    i = calc_service(user['call_date'])
    await message.answer(
        f"👤 <b>Профиль</b>\n\n"
        f"🪖 Имя: <b>{user['name']}</b>\n"
        f"📅 Дата призыва: <b>{user['call_date']}</b>\n"
        f"🏠 Часть: <b>{user['unit']}</b>\n"
        f"🏁 Дата дембеля: <b>{i['demob'].strftime('%d.%m.%Y')}</b>\n\n"
        f"📊 Пройдено: <b>{i['percentage']:.1f}%</b> ({i['passed_days']} дн.)",
        parse_mode='HTML',
        reply_markup=edit_kb(),
    )


@dp.callback_query(F.data == "edit_profile")
async def edit_profile_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Registration.name)
    await callback.message.answer("Давай обновим профиль.\n\nКак тебя зовут?")


# ─── Entry point ─────────────────────────────────────────────────────────────

async def main():
    await init_db()

    users = await get_all_users()
    for u in users:
        schedule_user_reminders(u['user_id'], u['call_date'])

    scheduler.start()
    logging.info("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
