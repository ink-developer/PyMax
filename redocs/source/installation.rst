Installation
=============

Требования
----------

- **Python 3.10+**
- pip или uv package manager

Установка через pip
--------------------

Самый простой способ установить PyMax:

.. code-block:: bash

    pip install -U maxapi-python

Или в виртуальном окружении:

.. code-block:: bash

    python -m venv venv
    source venv/bin/activate  # На Windows: venv\Scripts\activate
    pip install -U maxapi-python

Установка через uv (рекомендуется)
-----------------------------------

UV — это быстрый пакетный менеджер, написанный на Rust:

.. code-block:: bash

    uv add maxapi-python

Или добавить в ``pyproject.toml``:

.. code-block:: toml

    [project]
    dependencies = [
        "maxapi-python>=1.0.0",
    ]

Установка из исходников
------------------------

Для разработки или тестирования последней версии:

.. code-block:: bash

    git clone https://github.com/MaxApiTeam/PyMax.git
    cd PyMax
    pip install -e .

Или с использованием uv:

.. code-block:: bash

    git clone https://github.com/MaxApiTeam/PyMax.git
    cd PyMax
    uv sync

Проверка установки
-------------------

Проверить, что библиотека установлена корректно:

.. code-block:: python

    import pymax
    print(pymax.__version__)

Системные требования
--------------------

- **ОС**: Linux, macOS, Windows
- **Python**: 3.10, 3.11, 3.12, 3.13
- **Интернет**: Требуется для подключения к WebSocket серверу Max

.. note::

    Библиотека использует асинхронный I/O (asyncio), поэтому работает только в асинхронных контекстах.

Зависимости
-----------

Основные зависимости (устанавливаются автоматически):

- ``aiohttp`` — для HTTP запросов
- ``aiosqlite`` — для локального хранилища сессии
- ``pydantic`` — для валидации данных

Все зависимости указаны в ``pyproject.toml`` и устанавливаются автоматически.

Обновление
----------

Обновить до последней версии:

.. code-block:: bash

    pip install -U maxapi-python

Или через uv:

.. code-block:: bash

    uv add -U maxapi-python

Удаление
--------

Удалить библиотеку:

.. code-block:: bash

    pip uninstall maxapi-python

Или через uv:

.. code-block:: bash

    uv remove maxapi-python

Решение проблем
---------------

**ImportError: No module named 'pymax'**

    Убедитесь, что вы установили библиотеку:

    .. code-block:: bash

        pip install -U maxapi-python

**версия Python слишком старая**

    Обновите Python до 3.10 или новее:

    .. code-block:: bash

        python --version

**Ошибки зависимостей**

    Попробуйте переустановить:

    .. code-block:: bash

        pip install --force-reinstall -U maxapi-python
