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

        data = dependencies.db_manager.find_records(table_name=User.table, search_columns=['id_role', 'id'], search_values=[self.id_role, self.id])

        if data:
            self.id = data['id']
            self.id_role = data['id_role']

            self.id_chief = data['id_chief']
            self.fio = data['fio']
            self.active = bool(data['active'])
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
        self.id: Optional[Union[int]] = id

        self.name: Optional[str] = name
        self.active: bool = active

    def add(self):
        if not isinstance(self.id, int):
            raise ValueError(f"Идентификатор '{self.id}' должен быть целым числом.")
        if self.find(): # Используем self.id для поиска
            return "Пользователь с таким ID уже существует."
        dependencies.db_manager.insert(Cabinet.table, Cabinet.columns, [self.id, self.name, self.active])

    def update(self):
        """Сохраняет данные в БД."""
        dependencies.db_manager.update(Cabinet.table, Cabinet.columns,
                                      [self.id, self.name, self.active],
                                      condition_columns=['id'], condition_values=[self.id])

    def find(self):
        """Ищет по ID в БД."""
        if self.id is None:
            raise ValueError("ID не может быть None для операции поиска.")

        data = dependencies.db_manager.find_records(table_name=Cabinet.table, search_columns=['id'], search_values=[self.id])

        if data:
            self.id = data['id']
            self.id_role = data['id_role']

            self.id_chief = data['id_chief']
            self.name = data['name']
            self.active = bool(data['active'])
            return True
        else:
            return False


class Device:
    table = "Devices" 
    columns = ['id', 'id_cabinet', 'name', 'active']

    def __init__(
        self,
        id: int = None,
        id_cabinet: int = None,
        name: str = None,
        active: bool = True
    ):
        self.id = id
        self.id_cabinet: Optional[Union[int]] = id_cabinet
        self.name: Optional[str] = name
        self.active: bool = active

    def add(self):
        if not isinstance(self.id, int):
            raise ValueError(f"Идентификатор '{self.id}' должен быть целым числом.")
        if self.find(): # Используем self.id для поиска
            return "Пользователь с таким ID уже существует."
        dependencies.db_manager.insert(Device.table, Device.columns, [self.id_cabinet, self.name, self.active])

    def update(self):
        """Сохраняет данные в БД."""
        dependencies.db_manager.update(Device.table, Device.columns,
                                      [self.id_cabinet, self.name, self.active],
                                      condition_columns=['id'], condition_values=[self.id])

    def find(self):
        """Ищет по ID в БД."""
        if self.id is None:
            raise ValueError("ID не может быть None для операции поиска.")

        data = dependencies.db_manager.find_records(table_name=Device.table, search_columns=['id'], search_values=[self.id])

        if data:
            self.id = data['id']
            self.id_role = data['id_role']

            self.id_chief = data['id_chief']
            self.name = data['name']
            self.active = bool(data['active'])
            return True
        else:
            return False
    
    def all():
        pass

class StandartTask:
    table = "StandartTasks  " 
    columns = ['id', 'id_cabinet', 'id_device', 'name', 'is_parallel', 'time']

    def __init__(
        self,
        id: int = None,
        id_cabinet: int = None,
        id_device: int = None,
        name: str = None,
        is_parallel: bool = True,
        time_task: date = None
    ):
        self.id = id
        self.id_cabinet = id_cabinet
        self.id_device = id_device
        self.name = name
        self.is_parallel: bool = is_parallel
        self.time: date = time_task

    def add(self):
        if not isinstance(self.id, int):
            raise ValueError(f"Идентификатор '{self.id}' должен быть целым числом.")
        if self.find(): # Используем self.id для поиска
            return "Пользователь с таким ID уже существует."
        dependencies.db_manager.insert(StandartTask.table, StandartTask.columns, [self.id, self.id_cabinet, self.id_device, self.name, self.is_parallel, self.time])

    def update(self):
        """Сохраняет данные в БД."""
        dependencies.db_manager.update(StandartTask.table, StandartTask.columns,
                                      [self.id, self.id_cabinet, self.id_device, self.name, self.is_parallel, self.time],
                                      condition_columns=['id'], condition_values=[self.id])

    def find(self):
        """Ищет по ID в БД."""
        if self.id is None:
            raise ValueError("ID не может быть None для операции поиска.")

        data = dependencies.db_manager.find_records(table_name=StandartTask.table, search_columns=['id'], search_values=[self.id])

        if data:
            self.id = data['id']
            self.id_cabinet = data['id_cabinet']
            self.id_device = data['id_device']
            
            self.name = data['name']
            self.is_parallel = bool(data['is_parallel'])
            self.time = data['time']
            return True
        else:
            return False
    
    def all():
        pass


class Reservation:
    table = "Reservations" 
    columns = ['id', 'id_task', 'assistants', 'start_date', 'end_date']

    def __init__(
        self,
        id: int = None,
        id_task: int = None,
        assistants: str = None,
        start_date: str = None,
        end_date: bool = True,
    ):
        self.id = id
        self.id_task = id_task
        self.assistants = assistants
        self.start_date: date = start_date
        self.end_date: date = end_date

    def add(self):
        if not isinstance(self.id, int):
            raise ValueError(f"Идентификатор '{self.id}' должен быть целым числом.")
        if self.find(): # Используем self.id для поиска
            return "Пользователь с таким ID уже существует."
        dependencies.db_manager.insert(StandartTask.table, StandartTask.columns, [self.id, self.id_task, self.assistants, self.start_date, self.end_date])

    def update(self):
        """Сохраняет данные в БД."""
        dependencies.db_manager.update(StandartTask.table, StandartTask.columns,
                                      [self.id, self.id_task, self.assistants, self.start_date, self.end_date],
                                      condition_columns=['id'], condition_values=[self.id])

    def find(self):
        """Ищет по ID в БД."""
        if self.id is None:
            raise ValueError("ID не может быть None для операции поиска.")

        data = dependencies.db_manager.find_records(table_name=StandartTask.table, search_columns=['id'], search_values=[self.id])

        if data:
            self.id = data['id']
            self.id_task = data['id_task']
            self.assistants = data['assistants']
            self.start_date = data['start_date']
            self.end_date = data['end_date']
            return True
        else:
            return False
    
    def all():
        pass