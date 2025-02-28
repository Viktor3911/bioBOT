import json
import psycopg2
from psycopg2 import pool  # Для пула соединений
import logging
from typing import Any, Dict, Optional, overload

from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.base import StorageKey, StateType

from core.config import PG_DBNAME, PG_FSM_DBNAME, PG_HOST, PG_USER, PG_PORT, PG_PASSWORD

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s', )


class DatabaseConnection:
    """Вспомогательный класс для управления подключением к базе данных (Singleton)."""
    _instances = {}  # Словарь для хранения экземпляров по имени БД

    def __new__(cls, host, database, user, password, port=None):
        key = (host, database, user, password, port)
        if key not in cls._instances:
            instance = super(DatabaseConnection, cls).__new__(cls)
            instance.host = host
            instance.database = database
            instance.user = user
            instance.password = password
            instance.port = port
            instance._conn_pool = None
            cls._instances[key] = instance
        return cls._instances[key]

    def initialize_pool(self):
        """Инициализирует пул соединений после создания БД"""
        if self._conn_pool is None:
            self._create_connection_pool()

    def _create_connection_pool(self):
        """Создает пул соединений."""
        try:
            # print(f"self.host: \'{self.host}\'")
            # print(f"self.database: \'{self.database}\'")
            # print(f"self.user: \'{self.user}\'")
            # print(f"self.password: \'{self.password}\'")
            # print(f"self.port: \'{self.port}\'")

            # print("Host (repr):", repr(self.host))
            # print("Database (repr):", repr(self.database))
            # print("User (repr):", repr(self.user))
            # print("Password (repr):", repr(self.password))
            # print("Port (repr):", repr(self.port))

            self._conn_pool = pool.SimpleConnectionPool(
                minconn=1, maxconn=3,  # Настройте по необходимости
                host=self.host, database=self.database,
                user=self.user, password=self.password,
                port=self.port,
                client_encoding='utf8'
            )
            logging.info("Пул соединений успешно создан.")
        except psycopg2.Error as e:
            logging.error(f"Ошибка при создании пула соединений: {e}")
            raise

    def get_connection(self):
        """Получает соединение из пула."""
        if self._conn_pool is None:
            self._create_connection_pool()
        try:
            return self._conn_pool.getconn()
        except psycopg2.Error as e:
            logging.error(f"Ошибка при получении соединения из пула: {e}")
            raise

    def return_connection(self, conn):
        """Возвращает соединение в пул."""
        if self._conn_pool:
            self._conn_pool.putconn(conn)

    def close_all_connections(self):
        """Закрывает все соединения в пуле."""
        if self._conn_pool:
            self._conn_pool.closeall()
            logging.info("Все соединения пула закрыты.")
            self._conn_pool = None

    def create_database_if_not_exists(self):
        """Создает базу данных, если она не существует."""
        conn = None
        # print(f"self.host: \'{self.host}\'")
        # print(f"self.database: \'{self.database}\'")
        # print(f"self.user: \'{self.user}\'")
        # print(f"self.password: \'{self.password}\'")
        # print(f"self.port: \'{self.port}\'")

        try:
            conn = psycopg2.connect(host=self.host, user=self.user, password=self.password, port=self.port)
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.database,))
                exists = cursor.fetchone()
                if not exists:
                    logging.info(f"База данных '{self.database}' не существует. Создание...")
                    cursor.execute(f"CREATE DATABASE \"{self.database}\"")
                    logging.info(f"База данных '{self.database}' успешно создана.")
                else:
                    logging.info(f"База данных '{self.database}' уже существует.")
        except psycopg2.errors.DuplicateDatabase:
            logging.info(f"База данных '{self.database}' уже существует.")
        except psycopg2.Error as e:
            logging.error(f"Ошибка создания базы данных '{self.database}': {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def __del__(self):
        """Гарантирует закрытие пула при удалении экземпляра."""
        self.close_all_connections()


class PostgreSQLStorage(BaseStorage):
    """Хранилище состояний FSM (Singleton).""" 
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PostgreSQLStorage, cls).__new__(cls)
            cls._instance._db_conn = DatabaseConnection(
                host=PG_HOST,
                database=PG_FSM_DBNAME,
                user=PG_USER,
                password=PG_PASSWORD,
                port=PG_PORT
            )
        return cls._instance

    def __init__(self):
        # Инициализация происходит в __new__ только один раз
        pass

    def initialize(self):
        """Явная инициализация подключения после создания БД"""
        # Создаем БД если не существует
        self._db_conn.create_database_if_not_exists()
        # Инициализируем пул соединений
        self._db_conn.initialize_pool()
        # Создаем таблицы
        self._init_tables()

    def _connect(self):
        """Получает соединение из пула."""
        return self._db_conn.get_connection()

    def _init_tables(self):
        """Создает таблицу fsm_states, если она не существует."""
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS fsm_states (
                        chat_id BIGINT,
                        user_id BIGINT,
                        state TEXT,
                        data TEXT,
                        PRIMARY KEY (chat_id, user_id)
                    )
                """)
                conn.commit()
                logging.info("Таблица fsm_states успешно создана (если не существовала).")
        except psycopg2.Error as e:
            logging.error(f"Ошибка при создании таблицы fsm_states: {e}")
        finally:
            if conn:
                conn.close()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT state FROM fsm_states WHERE chat_id = %s AND user_id = %s",
                               (key.chat_id, key.user_id))
                result = cursor.fetchone()
                return result[0] if result else None
        except psycopg2.Error as e:
            logging.error(f"Ошибка при получении состояния пользователя {key.user_id} в чате {key.chat_id}: {e}")
            return None
        finally:
            self._db_conn.return_connection(conn)

    async def set_state(self, key: StorageKey, state: Optional[StateType] = None) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                state_name = state if state else None
                if state_name:
                    cursor.execute("""
                        INSERT INTO fsm_states (chat_id, user_id, state, data)
                        VALUES (%s, %s, %s, COALESCE((SELECT data FROM fsm_states WHERE chat_id = %s AND user_id = %s), '{}'))
                        ON CONFLICT (chat_id, user_id) DO UPDATE SET state = EXCLUDED.state, data = fsm_states.data;
                    """, (key.chat_id, key.user_id, state_name, key.chat_id, key.user_id))
                    logging.info(f"Состояние пользователя {key.user_id} в чате {key.chat_id} установлено на '{state_name}'.")
                else:
                    cursor.execute("DELETE FROM fsm_states WHERE chat_id = %s AND user_id = %s",
                                   (key.chat_id, key.user_id))
                    logging.info(f"Состояние пользователя {key.user_id} в чате {key.chat_id} сброшено.")
                conn.commit()
        except psycopg2.Error as e:
            logging.error(f"Ошибка при установке состояния пользователя {key.user_id} в чате {key.chat_id}: {e}")
        finally:
            self._db_conn.return_connection(conn)

    async def get_data(self, key: StorageKey) -> dict:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT data FROM fsm_states WHERE chat_id = %s AND user_id = %s",
                               (key.chat_id, key.user_id))
                result = cursor.fetchone()
                if result:
                    data = json.loads(result[0])
                    logging.info(f"Данные пользователя {key.user_id} в чате {key.chat_id} получены.")
                    return data
                else:
                    logging.info(f"Данные пользователя {key.user_id} в чате {key.chat_id} не найдены.")
                    return {}
        except psycopg2.Error as e:
            logging.error(f"Ошибка при получении данных пользователя {key.user_id} в чате {key.chat_id}: {e}")
            return {}
        finally:
            self._db_conn.return_connection(conn)

    async def set_data(self, key: StorageKey, data: dict) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO fsm_states (chat_id, user_id, state, data)
                    VALUES (%s, %s, COALESCE((SELECT state FROM fsm_states WHERE chat_id = %s AND user_id = %s), ''), %s)
                    ON CONFLICT (chat_id, user_id) DO UPDATE SET data = EXCLUDED.data;
                """, (key.chat_id, key.user_id, key.chat_id, key.user_id, json.dumps(data)))
                conn.commit()
                logging.info(f"Данные пользователя {key.user_id} в чате {key.chat_id} установлены: {data}")
        except psycopg2.Error as e:
            logging.error(f"Ошибка при установке данных пользователя {key.user_id} в чате {key.chat_id}: {e}")
        finally:
            self._db_conn.return_connection(conn)

    async def update_data(self, key: StorageKey, data: dict) -> None:
        current_data = await self.get_data(key)
        updated_data = {**current_data, **data}
        await self.set_data(key, updated_data)
        logging.info(f"Данные пользователя {key.user_id} в чате {key.chat_id} обновлены: {data}")

    async def reset_state(self, key: StorageKey, with_data: bool = True) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                if with_data:
                    cursor.execute("DELETE FROM fsm_states WHERE chat_id = %s AND user_id = %s",
                                   (key.chat_id, key.user_id))
                    logging.info(f"Состояние и данные пользователя {key.user_id} в чате {key.chat_id} сброшены.")
                else:
                    cursor.execute(
                        "UPDATE fsm_states SET state = NULL, data = '{}' WHERE chat_id = %s AND user_id = %s",
                        (key.chat_id, key.user_id)
                    )
                    logging.info(f"Состояние пользователя {key.user_id} в чате {key.chat_id} сброшено (данные очищены).")
                conn.commit()
        except psycopg2.Error as e:
            logging.error(f"Ошибка при сбросе состояния пользователя {key.user_id} в чате {key.chat_id}: {e}")
        finally:
            self._db_conn.return_connection(conn)

    async def close(self) -> None:
        """Закрывает все соединения пула."""
        self._db_conn.close_all_connections()
        logging.info("Соединение с базой данных PostgreSQL закрыто.")

    async def wait_closed(self) -> None:
        """Позволяет дождаться закрытия хранилища."""
        pass


class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._db_conn = DatabaseConnection(
                host=PG_HOST,
                database=PG_DBNAME,
                user=PG_USER,
                password=PG_PASSWORD,
                port=PG_PORT
            )
        return cls._instance

    def __init__(self):
        # Инициализация происходит в __new__ только один раз
        pass

    def initialize(self):
        """Явная инициализация подключения после создания БД"""
        # Создаем БД если не существует
        self._db_conn.create_database_if_not_exists()
        # Инициализируем пул соединений
        self._db_conn.initialize_pool()
        # Создаем таблицы
        self._init_tables()

    def _connect(self):
        """Получает соединение из пула."""
        return self._db_conn.get_connection()

    def _init_tables(self):
        """Создает таблицы в базе данных."""
        create_tables_sql = [
            """
            CREATE TABLE IF NOT EXISTS \"Roles\" (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS \"Users\" (
                id INTEGER PRIMARY KEY,
                id_role INTEGER,
                id_chief INTEGER,
                fio TEXT,
                active BOOLEAN,
                FOREIGN KEY (id_role) REFERENCES \"Roles\"(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS \"Cabinets\" (
                id SERIAL PRIMARY KEY,
                name TEXT,
                active BOOLEAN
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS \"Devices\" (
                id SERIAL PRIMARY KEY,
                id_cabinet INTEGER,
                name TEXT,
                active BOOLEAN,
                FOREIGN KEY (id_cabinet) REFERENCES \"Cabinets\"(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS \"StandartTasks\" (
                id SERIAL PRIMARY KEY,
                id_cabinet INTEGER,
                id_device INTEGER,
                name TEXT,
                is_parallel BOOLEAN,
                time DATE,
                FOREIGN KEY (id_cabinet) REFERENCES \"Cabinets\"(id),
                FOREIGN KEY (id_device) REFERENCES \"Devices\"(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS \"Reservations\" (
                id SERIAL PRIMARY KEY,
                id_task INTEGER,
                assistants TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                FOREIGN KEY (id_task) REFERENCES \"StandartTask\"(id)
            )
            """,
        ]

        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                for sql in create_tables_sql:
                    cursor.execute(sql)
                conn.commit()
            logging.info("Таблицы bio успешно созданы в PostgreSQL.")
        except psycopg2.Error as e:
            logging.error(f"Ошибка при создании таблиц PostgreSQL: {e}")
        finally:
            self._db_conn.return_connection(conn)

    def close(self):
        """Закрывает все соединения пула."""
        self._db_conn.close_all_connections()
        logging.info("Соединение с базой данных закрыто.")

    def insert(self, table_name: str, columns: list, values: list, use_id: bool = False):
        if len(columns) != len(values):
            logging.error("Ошибка: Количество столбцов и значений должно совпадать.")
            return None

        filtered_columns = [col for col, val in zip(columns, values) if val is not None]
        filtered_values = [val for val in values if val is not None]

        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                if table_name == "Orders":
                    cursor.execute("""
                        SELECT COALESCE(MAX(id), 0) + 1
                        FROM \"Orders\"
                        WHERE id_company = %s
                    """, (values[columns.index('id_company')],))
                    order_number = cursor.fetchone()[0]
                    filtered_columns.insert(0, 'id')
                    filtered_values.insert(0, order_number)

                placeholders = ", ".join("%s" for _ in filtered_columns)
                insert_query = f"INSERT INTO \"{table_name}\" ({', '.join(filtered_columns)}) VALUES ({placeholders})"
                cursor.execute(insert_query, filtered_values)
                conn.commit()
                logging.info(f"Запись успешно добавлена в таблицу {table_name}.")
                return order_number if table_name == "Orders" else True
        except psycopg2.Error as e:
            logging.error(f"Ошибка при вставке данных в таблицу {table_name}: {e}")
            return None
        finally:
            self._db_conn.return_connection(conn)

    def find_records(self, table_name: str, search_columns: list = None, search_values: list = None, multiple: bool = False, custom_query: str = None, query_params: tuple = None):
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                if custom_query:
                    cursor.execute(custom_query, query_params)
                elif search_columns and search_values:
                    if len(search_columns) != len(search_values):
                        raise ValueError("Количество столбцов и значений должно совпадать")
                    where_conditions = " AND ".join([f"{column} = %s" for column in search_columns])
                    query = f"SELECT * FROM \"{table_name}\" WHERE {where_conditions}"
                    cursor.execute(query, tuple(search_values))
                else:
                    query = f"SELECT * FROM \"{table_name}\""
                    cursor.execute(query)

                if multiple:
                    records = cursor.fetchall()
                    column_names = [desc[0] for desc in cursor.description]
                    return [dict(zip(column_names, record)) for record in records]
                else:
                    record = cursor.fetchone()
                    if record:
                        column_names = [desc[0] for desc in cursor.description]
                        return dict(zip(column_names, record))
                    return None
        except psycopg2.Error as e:
            logging.error(f"Ошибка при поиске записей в таблице {table_name}: {e}")
            return [] if multiple else None
        finally:
            self._db_conn.return_connection(conn)

    def update(self, table_name: str, set_columns: list, set_values: list,
               condition_columns: list, condition_values: list):
        if len(set_columns) != len(set_values) or len(condition_columns) != len(condition_values):
            logging.error("Ошибка: Количество столбцов и значений для обновления/условия должно совпадать.")
            return False

        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                where_conditions = " AND ".join([f"{col} = %s" for col in condition_columns])
                set_clause = ", ".join([f"{col} = %s" for col in set_columns])
                query = f"UPDATE \"{table_name}\" SET {set_clause} WHERE {where_conditions}"
                full_values = set_values + condition_values

                cursor.execute(f"SELECT 1 FROM \"{table_name}\" WHERE {where_conditions}", condition_values)
                if not cursor.fetchone():
                    logging.warning(f"Запись не найдена в таблице {table_name}.")
                    return False

                cursor.execute(query, full_values)
                conn.commit()

                if cursor.rowcount == 0:
                    logging.warning(f"Не удалось обновить запись в таблице {table_name}.")
                    return False

                logging.info(f"Успешно обновлено {cursor.rowcount} строк в таблице {table_name}.")
                return True
        except psycopg2.Error as e:
            logging.error(f"Ошибка при обновлении данных в таблице {table_name}: {e}")
            return False
        finally:
            self._db_conn.return_connection(conn)

    def delete(self, table_name: str, unique_column: str, unique_value):
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT 1 FROM \"{table_name}\" WHERE {unique_column} = %s", (unique_value,))
                if not cursor.fetchone():
                    logging.warning(f"Запись с уникальным значением {unique_value} не найдена в таблице {table_name}.")
                    return False

                delete_query = f"DELETE FROM \"{table_name}\" WHERE {unique_column} = %s"
                cursor.execute(delete_query, (unique_value,))
                conn.commit()
                logging.info(f"Запись с уникальным значением {unique_value} успешно удалена из таблицы {table_name}.")
                return True
        except psycopg2.Error as e:
            logging.error(f"Ошибка при удалении данных из таблицы {table_name}: {e}")
            return False
        finally:
            self._db_conn.return_connection(conn)
        """
        Удаляет запись из таблицы по уникальному столбцу.

        Args:
            table_name (str): Имя таблицы, из которой нужно удалить запись.
            unique_column (str): Столбец, по которому будет производиться поиск уникальной записи.
            unique_value (str, int, float): Значение уникального столбца, по которому будет удалена запись.

        Returns:
            bool: True, если запись успешно удалена, иначе False.
        """
        try:
            with self._connect() as db:
                with db.cursor() as cursor:
                    query = f"SELECT {unique_column} FROM \"{table_name}\" WHERE {unique_column} = %s"
                    cursor.execute(query, (unique_value,))
                    existing_record = cursor.fetchone()

                    if not existing_record:
                        logging.warning(f"Запись с уникальным значением {unique_value} не найдена в таблице {table_name}.")
                        return False

                    delete_query = f"DELETE FROM \"{table_name}\" WHERE {unique_column} = %s"
                    cursor.execute(delete_query, (unique_value,))

                    logging.info(f"Запись с уникальным значением {unique_value} успешно удалена из таблицы {table_name}.")
                    return True

        except psycopg2.Error as e:
            logging.error(f"Ошибка при удалении данных из таблицы {table_name}: {e}")
            return False


if __name__ == '__main__':
    pass
