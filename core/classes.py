from typing import List, Optional, Union
from typing import Tuple
from datetime import datetime, date, timedelta
import os
import random
import time
import logging
from core.utils import dependencies
import psycopg2

logging.basicConfig(level=logging.INFO)


class User:
    table = "Users" 
    columns = ['id', 'id_role', 'id_chief', 'fio', 'active']

    def __init__(
        self,
        id: int = None,
        id_chief: int = 0,
        fio: str = None,
        active: bool = True
    ):
        self.id_role = 2
        self.id: Optional[Union[int]] = id
        
        self.id_chief: Optional[Union[int]] = id_chief
        self.fio: Optional[str] = fio
        self.active: bool = active

    def add(self):
        if not isinstance(self.id, int):
            raise ValueError(f"Идентификатор '{self.id}' должен быть целым числом.")
        if self.find(): # Используем self.id для поиска
            return "Пользователь с таким ID уже существует."
        dependencies.db_manager.insert(User.table, User.columns, [self.id, self.id_role, self.id_chief, self.fio, self.active])

    def update(self):
        """Сохраняет данные пользователя в БД."""
        dependencies.db_manager.update(User.table, User.columns,
                                      [self.id, self.id_role, self.id_chief, self.fio, self.active],
                                      condition_columns=['id'], condition_values=[self.id])

    def find(self):
        """Ищет пользователя по ID в БД."""
        if self.id is None:
            raise ValueError("ID пользователя не может быть None для операции поиска.")

        user_data = dependencies.db_manager.find_records(table_name=User.table, search_columns=['id_role', 'id'], search_values=[self.id_role, self.id])

        if user_data:
            self.id = user_data['id']
            self.id_role = user_data['id_role']

            self.id_chief = user_data['id_chief']
            self.fio = user_data['fio']
            self.active = bool(user_data['active'])
            return True
        else:
            return False
        

class Cabinet:
    table = "Cabinets" 
    columns = ['id', 'name', 'active']

    def __init__(
        self,
        id: int = None,
        name: str = None,
        active: bool = True
    ):
        self.id_role = 2
        self.id: Optional[Union[int]] = id

        self.name: Optional[str] = name
        self.active: bool = active

    def add(self):
        if not isinstance(self.id, int):
            raise ValueError(f"Идентификатор '{self.id}' должен быть целым числом.")
        if self.find(): # Используем self.id для поиска
            return "Пользователь с таким ID уже существует."
        dependencies.db_manager.insert(User.table, User.columns, [self.id, self.name, self.active])

    def update(self):
        """Сохраняет данные в БД."""
        dependencies.db_manager.update(User.table, User.columns,
                                      [self.id, self.name, self.active],
                                      condition_columns=['id'], condition_values=[self.id])

    def find(self):
        """Ищет по ID в БД."""
        if self.id is None:
            raise ValueError("ID не может быть None для операции поиска.")

        user_data = dependencies.db_manager.find_records(table_name=User.table, search_columns=['id_role', 'id'], search_values=[self.id_role, self.id])

        if user_data:
            self.id = user_data['id']
            self.id_role = user_data['id_role']

            self.id_chief = user_data['id_chief']
            self.name = user_data['name']
            self.active = bool(user_data['active'])
            return True
        else:
            return False


class Device:
    table = "Devices" 
    columns = ['id', 'id_cabinet', 'name', 'active']

    def __init__(
        self,
        id: int = None,
        name: str = None,
        active: bool = True
    ):
        self.id_role = 2
        self.id: Optional[Union[int]] = id

        self.name: Optional[str] = name
        self.active: bool = active

    def add(self):
        if not isinstance(self.id, int):
            raise ValueError(f"Идентификатор '{self.id}' должен быть целым числом.")
        if self.find(): # Используем self.id для поиска
            return "Пользователь с таким ID уже существует."
        dependencies.db_manager.insert(User.table, User.columns, [self.id, self.name, self.active])

    def update(self):
        """Сохраняет данные в БД."""
        dependencies.db_manager.update(User.table, User.columns,
                                      [self.id, self.name, self.active],
                                      condition_columns=['id'], condition_values=[self.id])

    def find(self):
        """Ищет по ID в БД."""
        if self.id is None:
            raise ValueError("ID не может быть None для операции поиска.")

        user_data = dependencies.db_manager.find_records(table_name=User.table, search_columns=['id_role', 'id'], search_values=[self.id_role, self.id])

        if user_data:
            self.id = user_data['id']
            self.id_role = user_data['id_role']

            self.id_chief = user_data['id_chief']
            self.name = user_data['name']
            self.active = bool(user_data['active'])
            return True
        else:
            return False
