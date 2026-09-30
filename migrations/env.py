from alembic import context
from slms.models import Base

connection = context.config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Las migraciones requieren una conexión explícita desde Samtec Lockers.")
context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
with context.begin_transaction():
    context.run_migrations()
