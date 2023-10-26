import logging
import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy.orm import backref

import os
import io
import base64
import asyncio
import zlib


load_dotenv()

# Bot token can be obtained via https://t.me/BotFather
API_TOKEN = os.environ['BOT_TOKEN']

bot = Bot(token=API_TOKEN)

# Initialize the dispatcher
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)


# SQLAlchemy setup
DATABASE_URL = 'sqlite:///t_me_bot.db'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()


# Define a directory to save images
image_save_directory = "static/images"
tmp_image_save_directory = "static/temporary"


# Define a message model (for saving messages)
class Message(Base):
    __tablename__='message'
    id = Column(Integer, primary_key=True)
    created = Column(DateTime, default=datetime.now())
    message_text = Column(String)
    contact = Column(String)
    send = Column(Boolean, default=False)
    image = relationship("Image", backref=backref('message', passive_deletes=True), cascade='all, delete', lazy=True)


class Image(Base):
    __tablename__='image'
    id = Column(Integer, primary_key=True, index=True)
    base = Column(String)
    message_id = Column(Integer, ForeignKey('message.id', ondelete='CASCADE'))


class TelegramGroup(Base):
    __tablename__='group'
    id = Column(Integer, primary_key=True, index=True)
    gr_id = Column(String, unique= True)
    gr_name = Column(String)
    gr_link = Column(String)


Base.metadata.create_all(bind=engine)

# global vareable
st = False
var = True

class AddAdvertisement(StatesGroup):
    wait_for_body = State()
    wait_for_image = State()
    wait_for_contact = State()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton(text="Reklamalar")
    button1 = KeyboardButton(text="Reklama qo'shish")
    button2 = KeyboardButton(text="Guruhlarga yuborish")
    keyboard.add(button, button1).add(button2)
    await message.answer("Assalomu alekum", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text.lower() == "reklama qo'shish", state="*")
async def add_advertisement(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton(text="Rasm")
    button2 = KeyboardButton(text="Reklama matni")
    button3 = KeyboardButton(text="Kontakt")
    button4 = KeyboardButton(text="Saqlash")
    keyboard.add(button, button2, button3).add(button4)
    await message.answer("Tanlang", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text.lower() == 'reklama matni')
async def handle_add_body(message: types.Message, state: FSMContext):
    await state.set_state(AddAdvertisement.wait_for_body)
    await message.answer("Reklama matnini kiriting:")


@dp.message_handler(state=AddAdvertisement.wait_for_body)
async def add_body(message: types.Message, state: FSMContext):
    await state.update_data(message_body=message.text)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton(text="Rasm")
    button2 = KeyboardButton(text="Reklama matni")
    button3 = KeyboardButton(text="Kontakt")
    button4 = KeyboardButton(text="Saqlash")
    keyboard.add(button, button2, button3).add(button4)
    await state.reset_state(with_data=False)
    await message.answer("Qabul qilindi", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text.lower() == 'rasm')
async def handle_add_image(message: types.Message, state: FSMContext):
    await state.set_state(AddAdvertisement.wait_for_image)
    await message.answer("Rasm yuboring:")


@dp.message_handler(content_types=types.ContentType.PHOTO, state=AddAdvertisement.wait_for_image)
async def add_image(message: types.Message, state: FSMContext):
    data = await state.get_data()
    imgs = []
    if data.get("file_id"):
        imgs.extend(data["file_id"])
        imgs.append(message.photo[-1].file_id)
    else:
        imgs.append(message.photo[-1].file_id)
    await state.update_data(file_id = imgs)
    await state.reset_state(with_data=False)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton(text="Rasm")
    button2 = KeyboardButton(text="Reklama matni")
    button3 = KeyboardButton(text="Kontakt")
    button4 = KeyboardButton(text="Saqlash")
    keyboard.add(button, button2, button3).add(button4)
    await message.answer("Qabul qilindi", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text.lower() == 'kontakt')
async def handle_add_contact(message: types.Message, state: FSMContext):
    await state.set_state(AddAdvertisement.wait_for_contact)
    await message.answer("Kontakt kiriting:")


@dp.message_handler(state=AddAdvertisement.wait_for_contact)
async def add_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact = message.text.lower())
    await state.reset_state(with_data=False)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton(text="Rasm")
    button2 = KeyboardButton(text="Reklama matni")
    button3 = KeyboardButton(text="Kontakt")
    button4 = KeyboardButton(text="Saqlash")
    keyboard.add(button, button2, button3).add(button4)
    await message.answer("Qabul qilindi", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == 'Saqlash', state="*")
async def save_message(message: types.Message, state: FSMContext):
    session = Session()
    data = await state.get_data()
    if data.get('contact'):
        text = "\n" + data.get('message_body') + "\n\n Cantact: " + data.get('contact')
    else:
        text = "\n" + data.get('message_body')
    m = Message(
        message_text=text
    )
    session.add(m)
    session.flush()
    file_id = data.get('file_id')
    if file_id:
        for id in file_id:
            file_info = await bot.get_file(id)
            file_name = str(id) + ".jpg"
            destination_path = os.path.join(image_save_directory, file_name)
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            await bot.download_file(file_info.file_path, destination_path)
            image = Image(
                base = file_name,
                message_id = m.id
            )
            session.add(image)
    session.commit()
    session.close()
    await state.finish()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton(text="Reklamalar")
    button1 = KeyboardButton(text="Reklama qo'shish")
    button2 = KeyboardButton(text="Guruhlarga yuborish")
    keyboard.add(button, button1).add(button2)
    await message.answer("Saqlandi!", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text.lower() == 'reklamalar')
async def getadd(message: types.Message):
    chat_id = message.from_user.id
    session = Session()
    msgs = session.query(Message).all()
    for msg in msgs:
        msg_id = msg.id
        await get_addvertisement(chat_id, msg_id)


async def get_addvertisement(chat_id, msg_id):
    session = Session()
    photos = []
    msg = session.get(Message, msg_id)
    query = session.query(Image).filter(Image.message_id == msg_id)
    imgs = query.all()
    session.close()
    caption = msg.message_text
    buttons = [
        types.InlineKeyboardButton(text="O'chirish", callback_data=f"delete_{msg.id}"),
        types.InlineKeyboardButton(text="Tanlash", callback_data=f"callback_{msg.id}"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(*buttons)
    if len(imgs) >= 2:
        for img in imgs:
            filtered_file = [f for f in os.listdir(image_save_directory) if f == img.base]
            path = image_save_directory + "/" + filtered_file[0]
            photos.append(types.InputMediaPhoto(
                media=open(path, "rb"),
                caption=caption
            ))
            caption = None
        await bot.send_media_group(chat_id, media=photos)  
    elif imgs:
        filtered_file = [f for f in os.listdir(image_save_directory) if f == imgs[0].base]
        with open(image_save_directory + "/" + filtered_file[0], "rb") as image:
            await bot.send_photo(chat_id, image, caption=msg.message_text, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text=msg.message_text)


async def send_to_group(msg_id):
    session = Session()
    photos = []
    msg = session.get(Message, msg_id)
    query = session.query(Image).filter(Image.message_id == msg_id)
    imgs = query.all()
    caption = msg.message_text
    gr_ids = session.query(TelegramGroup).all()
    for chat_id in gr_ids:
        if len(imgs) >= 2:
            for img in imgs:
                filtered_file = [f for f in os.listdir(image_save_directory) if f == img.base]
                path = image_save_directory + "/" + filtered_file[0]
                photos.append(types.InputMediaPhoto(
                    media=open(path, "rb"),
                    caption=caption
                ))
                caption = None
            try:
                await bot.send_media_group(int(chat_id.gr_id), media=photos)  
                session.close()
            except:
                session.delete(chat_id)
                session.commit()
                session.close()
        elif imgs:
            filtered_file = [f for f in os.listdir(image_save_directory) if f == imgs[0].base]
            with open(image_save_directory + "/" + filtered_file[0], "rb") as image:
                try:
                    await bot.send_photo(int(chat_id.gr_id), image, caption=msg.message_text)
                    session.close()
                except:
                    session.delete(chat_id)
                    session.commit()
                    session.close()
        else:
            try:
                await bot.send_message(int(chat_id.gr_id), text=msg.message_text)
                session.close()
            except:
                session.delete(chat_id)
                session.commit()
                session.close()


@dp.message_handler(content_types=[types.ContentType.NEW_CHAT_MEMBERS])
async def on_new_chat_members(message: types.Message):
    new_members = message.new_chat_members
    session = Session()
    bot_info = await bot.me
    for member in new_members:
        if member.is_bot and member.username == bot_info.username:
            chat_id = message.chat.id
            print(chat_id)
            gr_name = message.chat.title
            gr_link = message.chat.invite_link
            group = session.get(TelegramGroup, chat_id)
            if not group:
                gr = TelegramGroup(gr_id=chat_id, gr_name=gr_name, gr_link=gr_link)
                session.add(gr)
                session.commit()
                query = session.query(Message).filter(Message.send == True)
                msg = query.first()
                await send_to_group(msg.id)


@dp.message_handler(lambda message: message.text.lower() == 'guruhlarga yuborish')
async def send(message: types.Message):
    global st
    if not st:
        st = True
        await send_loop()
        await message.reply("Ok")
    await message.reply("Ok")


@dp.message_handler(commands=['stop'])
async def stop_send():
    global var
    var = False


async def send_loop(): 
    session = Session()
    query = session.query(Message).filter(Message.send == True)
    msg = query.first()
    session.close()
    if msg:
        while var:
            query = session.query(Message).filter(Message.send == True)
            msg = query.first()
            await send_to_group(msg.id)
            await asyncio.sleep(30)  # Sleep for 5 minutes (300 seconds)
    else:
        await bot.send_message(chat_id, text="No messages yet")


@dp.callback_query_handler(lambda c: c.data.startswith("callback_"))
async def update_status(call: types.CallbackQuery):
    session = Session()
    query = session.query(Message).filter(Message.send == True)
    m = query.first()
    if m:
        m.send = False
    msg = session.get(Message, call.data.split('_')[1])
    msg.send = True
    session.commit()
    session.close()
    await call.answer("Selected")


@dp.callback_query_handler(lambda c: c.data.startswith("delete_"))
async def delete_advertisement(call: types.CallbackQuery):
    id = int(call.data.split('_')[1])
    try:
        session = Session()
        imgs = session.query(Image).with_entities(Image.base).filter(Image.message_id == id).all()
        m = session.get(Message, id)
        for img in imgs:
            print(type(img))
            os.remove(image_save_directory + '/' + img.base)
        session.delete(m)
        session.commit()
        session.close()
        await call.answer("O'chirildi")
    except:
        await call.answer("Something went wrong")


# Start the bot
if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)

