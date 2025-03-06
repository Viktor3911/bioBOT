from core.utils import dependencies
from core.classes import User
from core.settings import FIRST, SECOND

dependencies.db_manager.initialize()

table = "Roles"
columns = ["id", "name"]

values = [0, "admin"]
success = dependencies.db_manager.insert(table, columns, values)

values = [1, "director"]
success = dependencies.db_manager.insert(table, columns, values)

values = [2, "assistant"]
success = dependencies.db_manager.insert(table, columns, values)

# director = User(id=FIRST, id_role=User.ROLE_DIRECTOR, fio='фио директора')
# director.add()

