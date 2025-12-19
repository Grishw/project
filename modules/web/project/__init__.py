# modules/web/project/__init__.py

from .blueprint import project_bp

# ВАЖНО: просто импортируем файлы с маршрутами
from . import upload
from . import select
from . import preprocess
from . import train
from . import forecast
