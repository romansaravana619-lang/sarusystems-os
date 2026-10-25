from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.core.database import Base
from app.shared import models  # noqa: F401
from app.clients import models as client_models  # noqa: F401
from app.sales import models as sales_models  # noqa: F401
from app.tasks import models as task_models  # noqa: F401
from app.services import models as service_models  # noqa: F401
from app.company import models as company_models  # noqa: F401
from app.command_center import models as command_center_models  # noqa: F401
from app.projects import models as project_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction(): context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config({"sqlalchemy.url": settings.database_url}, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()

if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
