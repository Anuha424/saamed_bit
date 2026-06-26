import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile, InputMediaPhoto
from aiogram.filters import Command

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '7958293117:AAGaQqM3aLgyrxBPvENxafO3R6d0QO0gnjs'
PRICE_LIST = {
    "Эндофем Про Супп №10": {"price": 125000, "nds": 15000},
    "Ловикс 150 мл": {"price": 107143, "nds": 12857.16},
    "Октенидин+Мирамистин 100 мл": {"price": 53575, "nds": 6429},
    "Октенидин+Мирамистин 50 мл": {"price": 50000, "nds": 6000},
}

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class OrderState(StatesGroup):
    choosing_product = State()
    entering_quantity = State()
    after_product = State()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_product_kb():
    buttons = [[KeyboardButton(text=f"💊 {name}")] for name in PRICE_LIST.keys()]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def get_action_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Продолжить покупки"), KeyboardButton(text="✅ Оформить заказ")]
    ], resize_keyboard=True)

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.set_data({'cart': []})

    # Путь к папке img
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_folder = os.path.join(base_dir, "img")

    # Отправка фото
    photo_files = ["1.png", "2.png", "3.png"]
    media_group = []
    for p in photo_files:
        path = os.path.join(img_folder, p)
        if os.path.exists(path):
            media_group.append(InputMediaPhoto(media=FSInputFile(path)))

    if media_group:
        await message.answer_media_group(media=media_group)

    welcome_text = """
🌟 *Добро пожаловать в SAA MED!* 🌟

Мы рады видеть вас в нашем магазине качественной медицинской продукции! 💊

📋 *Как сделать заказ:*
1️⃣ Выберите товар из списка ниже
2️⃣ Укажите необходимое количество
3️⃣ Добавьте в корзину или оформите заказ

━━━━━━━━━━━━━━━━━━━━
✨ *Наш ассортимент:*
"""

    for name, info in PRICE_LIST.items():
        total = info['price'] + info['nds']
        welcome_text += f"\n💊 *{name}*\n   💰 {total:,.0f} сум"

    welcome_text += "\n\n👇 *Выберите товар:*"

    await message.answer(welcome_text, reply_markup=get_product_kb(), parse_mode="Markdown")
    await state.set_state(OrderState.choosing_product)

@dp.message(OrderState.choosing_product)
async def choose_product(message: types.Message, state: FSMContext):
    # Убираем эмодзи из текста для сравнения
    product_name = message.text.replace("💊 ", "")

    if product_name not in PRICE_LIST:
        return await message.answer(
            "⚠️ *Ошибка!*\n\nПожалуйста, выберите товар из списка ниже, нажав на кнопку.",
            reply_markup=get_product_kb(),
            parse_mode="Markdown"
        )

    await state.update_data(current_product=product_name)

    info = PRICE_LIST[product_name]
    price_with_nds = info['price'] + info['nds']

    product_info = f"""
📦 *Выбранный товар:*
━━━━━━━━━━━━━━━━━━━━
💊 *{product_name}*
💰 Цена: {price_with_nds:,.0f} сум (включая НДС)
━━━━━━━━━━━━━━━━━━━━

🔢 *Введите количество* (в штуках):
"""

    await message.answer(product_info, parse_mode="Markdown")
    await state.set_state(OrderState.entering_quantity)

@dp.message(OrderState.entering_quantity)
async def enter_qty(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        return await message.answer(
            "❌ *Неверный формат!*\n\nПожалуйста, введите целое положительное число.\n\n💡 *Пример:* `5`",
            parse_mode="Markdown"
        )

    quantity = int(message.text)
    data = await state.get_data()
    cart = data.get('cart', [])
    cart.append({'name': data['current_product'], 'qty': quantity})
    await state.update_data(cart=cart)

    info = PRICE_LIST[data['current_product']]
    item_total = (info['price'] + info['nds']) * quantity

    success_msg = f"""
✅ *Товар добавлен в корзину!*

🛒 *Что в корзине:*
"""

    cart_total = 0
    for item in cart:
        item_info = PRICE_LIST[item['name']]
        item_cost = (item_info['price'] + item_info['nds']) * item['qty']
        cart_total += item_cost
        success_msg += f"• {item['name']}: {item['qty']} шт. — {item_cost:,.0f} сум\n"

    success_msg += f"\n💰 *Общая сумма:* {cart_total:,.0f} сум"
    success_msg += "\n\n👇 *Что дальше?*"

    await message.answer(success_msg, reply_markup=get_action_kb(), parse_mode="Markdown")
    await state.set_state(OrderState.after_product)

@dp.message(OrderState.after_product, F.text == "🛒 Продолжить покупки")
async def continue_buying(message: types.Message, state: FSMContext):
    await message.answer(
        "🛍️ *Продолжаем покупки!*\n\nВыберите следующий товар из списка:",
        reply_markup=get_product_kb(),
        parse_mode="Markdown"
    )
    await state.set_state(OrderState.choosing_product)

@dp.message(OrderState.after_product, F.text == "✅ Оформить заказ")
async def finish_order(message: types.Message, state: FSMContext):
    data = await state.get_data()

    summary = """
╔══════════════════════════════╗
║      📋 *ВАШ ЗАКАЗ* 📋       ║
╚══════════════════════════════╝

"""

    total_sum, total_nds = 0, 0
    item_number = 1

    for item in data['cart']:
        info = PRICE_LIST[item['name']]
        cost = info['price'] * item['qty']
        nds = info['nds'] * item['qty']
        item_total = cost + nds

        summary += f"*{item_number}. {item['name']}*\n"
        summary += f"   📦 Количество: {item['qty']} шт.\n"
        summary += f"   💰 Стоимость: {item_total:,.0f} сум\n"
        summary += f"   📊 НДС: {nds:,.0f} сум\n"
        summary += "   ───────────────────\n"

        total_sum += cost
        total_nds += nds
        item_number += 1

    grand_total = total_sum + total_nds

    summary += f"""
💎 *ИТОГО К ОПЛАТЕ:*
━━━━━━━━━━━━━━━━━━━━
💰 Сумма без НДС: {total_sum:,.0f} сум
📊 НДС: {total_nds:,.0f} сум
✨ *ОБЩАЯ СУММА: {grand_total:,.0f} сум* ✨
━━━━━━━━━━━━━━━━━━━━

🏢 *КОНТАКТЫ SAA MED:*
━━━━━━━━━━━━━━━━━━━━
📍 Адрес: Toshkent Shahri, Uchtepa tumani
🏦 Банк: Biznesni rivojlantirish banki
💳 Р/С: 2020 8000 1074 2309 5001
━━━━━━━━━━━━━━━━━━━━

🎉 *Спасибо за заказ!*
💬 Мы свяжемся с вами в ближайшее время.
"""

    await message.answer(summary, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())