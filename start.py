from core.utils import dependencies
from core.classes import User
from core.settings import FIRST_ADMIN

dependencies.db_manager.initialize()

table = "Roles"
columns = ["id", "name"]

values = [0, "admin"]
success = dependencies.db_manager.insert(table, columns, values)

values = [1, "director"]
success = dependencies.db_manager.insert(table, columns, values)

values = [2, "assistant"]
success = dependencies.db_manager.insert(table, columns, values)

admin = User(id=FIRST_ADMIN, id_role=User.ROLE_ADMIN, fio='admin')
admin.add()
