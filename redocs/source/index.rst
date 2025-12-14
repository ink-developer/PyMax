.. raw:: html

    <div style="margin-top:2rem;"></div>

.. image:: _static/logo.svg
   :align: center
   :width: 320px
PyMax
=====

.. raw:: html

    <p align="center" style="margin-top:0.6rem;">
      <img src="https://img.shields.io/badge/python-3.10+-3776AB.svg" alt="Python 3.10+">
      <img src="https://img.shields.io/badge/License-MIT-2f9872.svg" alt="License: MIT">
      <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff">
      <img src="https://img.shields.io/badge/packaging-uv-D7FF64.svg" alt="Packaging">
    </p>

.. rubric:: Кратко

**pymax** — асинхронная Python-библиотека для работы с внутренним API мессенджера Max.
Упрощает отправку сообщений, управление чатами/каналами и работу с историей через WebSocket.

.. toctree::
   :maxdepth: 2
   :titlesonly:
   :caption: Содержание

   installation
   quickstart
   clients
   types
   decorators
   examples
   guides

.. rubric:: Особенности

- Вход по номеру телефона
- Отправка / редактирование / удаление сообщений
- Управление чатами, каналами и диалогами
- Получение истории сообщений

---

Disclaimer
----------

.. warning::

   Это **неофициальная** библиотека для работы с внутренним API Max.
   Использование может **нарушать условия предоставления услуг**.
   Вы используете её на свой страх и риск — разработчики не несут ответственности
   за блокировку аккаунтов, потерю данных или юридические последствия.

---

Установка
---------

Требуется Python 3.10+.

.. code-block:: bash

    pip install -U maxapi-python

или через uv:

.. code-block:: bash

    uv add -U maxapi-python

---

Быстрый старт
-------------

Небольшой рабочий пример и описание в `quickstart`.

Документация
------------

- `GitHub Pages <https://maxapiteam.github.io/PyMax/>`_
- `DeepWiki <https://deepwiki.com/MaxApiTeam/PyMax>`_

Лицензия
--------

Проект распространяется под MIT (см. LICENSE).

Новости
-------

- `Telegram <https://t.me/pymax_news>`_

Star History
------------

.. image:: https://api.star-history.com/svg?repos=ink-developer/PyMax&type=date&legend=top-left

Авторы
------

- `ink <https://github.com/ink-developer>`_ — главный разработчик
- `noxzion <https://github.com/noxzion>`_ — оригинальный автор

Контрибьюторы
-------------

.. image:: https://contrib.rocks/image?repo=ink-developer/PyMax
   :alt: Contributors
