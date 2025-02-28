import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, KeyboardButton, ReplyKeyboardBuilder
from aiogram import Router

from core.utils import dependencies

router = Router()

class RegistrationState(StatesGroup):
    waiting_for_fio = State()


async def register_message(fio: str = None):
    message = "Регистрация:\n\n"
    message += f"ФИО: {fio if fio else 'Не указано'}\n"

    return message


async def confirmation_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Подтвердить", callback_data="confirm_reg")
    builder.button(text="Изменить ФИО", callback_data="edit_fio")


@router.message(CommandStart(deep_link=True, magic=F.args.regexp(re.compile(r'[a-f0-9]+'))))
async def cmd_start_register(message: Message, command: CommandObject, state: FSMContext):
    link = command.args

    worker = Worker()
    find = worker.find(id=message.from_user.id)
    if find and not worker.active:
        return

    company = db_manager.find_records(Company.table, ['link_workers'], [link])
    if company:
        await state.set_state(RegistrationState.waiting_for_fio)
        await state.update_data(role="worker", id_company=company['id'])
        await message.answer("Введите ваше ФИО:")
        return

    company = db_manager.find_records(Company.table, ['link_directors'], [link])
    if company:
        await state.set_state(RegistrationState.waiting_for_fio)
        await state.update_data(role="director", id_company=company['id'])
        await message.answer("Введите ваше ФИО:")
        return
    
    print(hashlib.sha256(str(message.from_user.id).encode()).hexdigest())
    link_admin = db_manager.find_records(Admin.table_link, ['link_admins'], [hashlib.sha256(str(message.from_user.id).encode()).hexdigest()])
    if link_admin:
        await state.set_state(RegistrationState.waiting_for_fio)
        await state.update_data(role="admin")
        await message.answer("Введите ваше ФИО:")
        return
    
    await message.answer("Здравствуйте! Используйте корректную ссылку для регистрации.")


@router.message(RegistrationState.waiting_for_fio)
async def process_fio(message: Message, state: FSMContext):
    await state.update_data(fio=message.text)
    data = await state.get_data()

    if data.get('phone_number'):
        await state.set_state(RegistrationState.waiting_for_confirmation)
        await message.answer(
            await register_message(data.get('fio'), data.get('phone_number')),
            reply_markup=await confirmation_keyboard()
        )
    else:
        await state.set_state(RegistrationState.waiting_for_number)
        await message.answer(
            "Введите ваш номер телефона вручную или нажмите кнопку для отправки:",
            reply_markup=await phone_number_keyboard()
        )


async def confirm_registration(callback_query: CallbackQuery, state: FSMContext, worker_main_keyboard, director_main_keyboard):
    user_id = callback_query.from_user.id
    data = await state.get_data()

    role = data.get('role')
    id_company = data.get('id_company', None)
    fio = data.get('fio')
    phone_number = data.get('phone_number')

    if role == "worker":
        admin = Admin()
        worker=Worker()
        director = Director()

        if director.find(user_id) or worker.find(user_id) or admin.find(user_id):
            worker = Worker(id=user_id, id_company=id_company, fio=fio, phone_number=phone_number)
            worker.update()
        else:
            worker = Worker(id=user_id, id_company=id_company, fio=fio, phone_number=phone_number)
            worker.add()

        await callback_query.message.answer("Регистрация завершена. Добро пожаловать!", reply_markup=await worker_main_keyboard())
        await callback_query.message.delete()
    elif role == "director":
        admin = Admin()
        worker=Worker()
        director = Director()

        if director.find(user_id) or worker.find(user_id) or admin.find(user_id):
            director = Director(id=user_id, id_company=id_company, fio=fio, phone_number=phone_number)
            director.update()
        else:
            director = Director(id=user_id, id_company=id_company, fio=fio, phone_number=phone_number)
            director.add()


        await callback_query.message.answer("Регистрация завершена. Вы зарегистрированы как начальник компании.", reply_markup=await director_main_keyboard())
        await callback_query.message.delete()

    elif role == "admin":
        admin = Admin()
        worker=Worker()
        director = Director()

        if director.find(user_id) or worker.find(user_id) or admin.find(user_id):
            admin = Admin(id=user_id, fio=fio, phone_number=phone_number)
            admin.update()
        else:
            admin = Admin(id=user_id, fio=fio, phone_number=phone_number)
            admin.add()

        # admin.delete_link(hashlib.sha256(str(user_id).encode()).hexdigest())
        await callback_query.message.answer("Регистрация завершена. Вы зарегистрированы как администратор.")
        await callback_query.message.delete()

    await state.set_state(state="null")


@router.callback_query(F.data == "edit_fio")
async def edit_fio(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(RegistrationState.waiting_for_fio)
    await callback_query.message.edit_text("Введите заново ваше ФИО:")