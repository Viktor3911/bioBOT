from typing import Any, Dict, Optional, overload

from aiogram.fsm.context import FSMContext as BaseFSMContext
from aiogram.fsm.storage.base import StorageKey, StateType
from aiogram.fsm.state import State
from core.sql import PostgreSQLStorage 


class CustomFSMContext(BaseFSMContext):
    def __init__(self, storage: PostgreSQLStorage, key: StorageKey):
        super().__init__(storage, key)
        self.storage: PostgreSQLStorage = storage
        self.key: StorageKey = key

    async def set_state(self, state: Optional[StateType] = None) -> None:
        """Устанавливает состояние, всегда преобразуя в строковое представление."""
        state_name = state.state if isinstance(state, State) else state
        await self.storage.set_state(key=self.key, state=str(state_name) if state_name else None)

    async def get_state(self) -> Optional[StateType]:
        state_str = await self.storage.get_state(key=self.key)
        return State(state_str) if state_str else None

    async def set_data(self, data: Dict[str, Any]) -> None:
        await self.storage.set_data(key=self.key, data=data)

    async def get_data(self) -> Dict[str, Any]:
        return await self.storage.get_data(key=self.key)

    async def get_value(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        data = await self.get_data()
        return data.get(key, default)

    async def update_data(
        self, data: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        if data:
            kwargs.update(data)
        current_data = await self.get_data()
        current_data.update(kwargs)
        await self.storage.set_data(key=self.key, data=current_data)  # Вернули key=self.key
        return current_data.copy()

    async def clear(self) -> None:
        await self.storage.set_state(key=self.key, state=None)
        await self.storage.set_data(key=self.key, data={})