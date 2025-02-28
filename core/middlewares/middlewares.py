from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import TelegramObject, Update
from core.utils.context import CustomFSMContext
from core.sql import PostgreSQLStorage

class CustomFSMContextMiddleware(BaseMiddleware):
    def __init__(self, storage: PostgreSQLStorage): 
        self.storage = storage

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Update):
            chat = None
            user = None
            bot_id = event.bot.id

            if event.message:
                chat = event.message.chat
                user = event.message.from_user
            elif event.callback_query:
                chat = event.callback_query.message.chat
                user = event.callback_query.from_user
            elif event.inline_query:
                user = event.inline_query.from_user
            # Добавьте обработку других типов обновлений, если необходимо

            if chat and user:
                key = StorageKey(bot_id=bot_id, chat_id=chat.id, user_id=user.id)
                fsm_context = CustomFSMContext(storage=self.storage, key=key)
                data["state"] = fsm_context

        return await handler(event, data)