from core.sql import PostgreSQLStorage, DatabaseManager 
from aiogram import Bot

db_manager = DatabaseManager()
storage = PostgreSQLStorage()

bot: Bot = None