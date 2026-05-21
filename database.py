import sqlite3
from pathlib import Path


def get_connection(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database(database_path):
    database_file = Path(database_path)
    database_file.parent.mkdir(parents=True, exist_ok=True)

    with get_connection(database_file) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                category TEXT NOT NULL,
                room TEXT,
                priority TEXT NOT NULL,
                description TEXT,
                contact TEXT,
                status TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                assignee_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (author_id) REFERENCES users (id),
                FOREIGN KEY (assignee_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (ticket_id) REFERENCES tickets (id),
                FOREIGN KEY (author_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                changed_by INTEGER NOT NULL,
                changed_at TEXT NOT NULL,
                FOREIGN KEY (ticket_id) REFERENCES tickets (id),
                FOREIGN KEY (changed_by) REFERENCES users (id)
            );
            """
        )

        has_users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if has_users:
            return

        users = [
            ("student1", "student123", "Алина Студентова", "student"),
            ("teacher1", "teacher123", "Игорь Преподаватель", "teacher"),
            ("executor1", "executor123", "Мария Исполнитель", "executor"),
            ("admin1", "admin123", "Ольга Администратор", "admin"),
            ("student2", "labpass2026", "Никита Практикант", "student"),
            ("teacher2", "method2026", "Светлана Методист", "teacher"),
        ]
        connection.executemany(
            "INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)",
            users,
        )

        tickets = [
            (
                "Не включается проектор в 305",
                "техника",
                "305",
                "высокий",
                "После пары проектор перестал реагировать на пульт и кнопку питания.",
                "student1@college.local",
                "новая",
                1,
                None,
                "19.05.2026 09:20",
                "19.05.2026 09:20",
            ),
            (
                "Нет доступа к электронному журналу",
                "доступы",
                "214",
                "средний",
                "После смены пароля журнал открывается с ошибкой доступа.",
                "teacher1, внутренний 118",
                "в работе",
                2,
                3,
                "02.05.2026 11:05",
                "03.05.2026 10:40",
            ),
            (
                "1С не сохраняет ведомость практики",
                "1С",
                "Лаборатория 1С",
                "критический",
                "При сохранении формы ведомости появляется сообщение о блокировке.",
                "+7 900 111-22-33",
                "ожидает ответа",
                2,
                3,
                "30.04.2026 16:15",
                "05.05.2026 12:10",
            ),
            (
                "Сломан разъём HDMI",
                "техника",
                "107",
                "низкий",
                "Кабель держится неплотно на преподавательском столе.",
                "student1 в чате группы",
                "решена",
                1,
                3,
                "11.05.2026 08:45",
                "12.05.2026 14:30",
            ),
            (
                "В аудитории 412 нет маркеров",
                "аудитория",
                "412",
                "низкий",
                "На доске остался только высохший маркер.",
                "teacher2@college.local",
                "закрыта",
                6,
                None,
                "07.05.2026 13:00",
                "07.05.2026 15:40",
            ),
            (
                "Очень длинная тема заявки о том что в компьютерном классе одновременно пропадают сеть звук изображение на интерактивной панели и вход в учебный портал",
                "техника",
                "К-203",
                "критический",
                "Проблема повторяется на нескольких рабочих местах во время защиты лабораторных.",
                "student2@college.local",
                "в работе",
                5,
                3,
                "21.05.2026 08:10",
                "21.05.2026 08:40",
            ),
            (
                "Не открывается Wi-Fi для гостевой лекции",
                "доступы",
                "Актовый зал",
                "высокий",
                "Лектору нужен гостевой доступ на время занятия.",
                "доб. 204",
                "новая",
                2,
                None,
                "15.05.2026 10:05",
                "15.05.2026 10:05",
            ),
            (
                "Громко шумит системный блок",
                "техника",
                "209",
                "средний",
                "Шум слышен на записи демонстрации экрана.",
                "student2",
                "закрыта",
                5,
                3,
                "18.04.2026 17:30",
                "20.04.2026 09:15",
            ),
            (
                "Нужен доступ к папке дипломов",
                "доступы",
                "методкабинет",
                "высокий",
                "Не открывается общая папка для проверки материалов.",
                "teacher1@college.local",
                "ожидает ответа",
                2,
                3,
                "09.05.2026 12:25",
                "10.05.2026 10:00",
            ),
            (
                "Не хватает стульев на олимпиаде",
                "аудитория",
                "Спортзал",
                "средний",
                "Перед началом мероприятия нужно добавить шесть стульев.",
                "оргкомитет",
                "закрыта",
                6,
                None,
                "01.05.2026 07:50",
                "01.05.2026 08:35",
            ),
            (
                "Ошибка печати справки из 1С",
                "1С",
                "118",
                "средний",
                "Печатная форма открывается пустой.",
                "teacher2",
                "новая",
                6,
                None,
                "20.05.2026 14:55",
                "20.05.2026 14:55",
            ),
            (
                "Подключить учебный стенд к сети",
                "другое",
                "311",
                "высокий",
                "Нужно проверить порт перед демонстрацией проекта.",
                "+7 900 555-01-01",
                "в работе",
                1,
                3,
                "06.05.2026 09:40",
                "06.05.2026 11:15",
            ),
        ]
        connection.executemany(
            """
            INSERT INTO tickets (
                subject, category, room, priority, description, contact, status,
                author_id, assignee_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tickets,
        )

        comments = [
            (1, 1, "Проверили другой пульт, результата нет.", "19.05.2026 09:40"),
            (1, 3, "Возьму проектор в обход после второй пары.", "19.05.2026 10:10"),
            (2, 2, "Ошибка появилась после обновления учётной записи.", "02.05.2026 11:15"),
            (2, 3, "Нужен скриншот сообщения при входе.", "03.05.2026 10:40"),
            (3, 2, "Ведомость нужна до конца дня.", "30.04.2026 16:20"),
            (3, 3, "Проверяю блокировки в базе учебного контура.", "05.05.2026 12:10"),
            (4, 1, "Можно использовать запасной кабель из 108.", "11.05.2026 09:10"),
            (5, 6, "Маркеры нашли в лаборантской.", "07.05.2026 15:30"),
            (6, 5, "Сбой повторился на защите проекта.", "21.05.2026 08:15"),
            (6, 3, "Проверяю коммутатор и панель.", "21.05.2026 08:40"),
            (7, 2, "Гость приедет к 12:00.", "15.05.2026 10:20"),
            (8, 5, "После очистки корпуса стало тише.", "20.04.2026 09:10"),
            (9, 2, "Папка нужна для комиссии.", "09.05.2026 12:35"),
            (10, 6, "Стулья перенесли из соседней аудитории.", "01.05.2026 08:35"),
            (11, 6, "Проблема есть у двух преподавателей.", "20.05.2026 15:05"),
            (12, 1, "Стенд стоит у окна, порт подписан DEV-3.", "06.05.2026 09:50"),
        ]
        connection.executemany(
            "INSERT INTO comments (ticket_id, author_id, body, created_at) VALUES (?, ?, ?, ?)",
            comments,
        )

        history = [
            (1, None, "новая", 1, "19.05.2026 09:20"),
            (2, None, "новая", 2, "02.05.2026 11:05"),
            (2, "новая", "в работе", 3, "03.05.2026 10:40"),
            (3, None, "новая", 2, "30.04.2026 16:15"),
            (3, "новая", "ожидает ответа", 3, "05.05.2026 12:10"),
            (4, None, "новая", 1, "11.05.2026 08:45"),
            (4, "новая", "решена", 3, "12.05.2026 14:30"),
            (5, None, "новая", 6, "07.05.2026 13:00"),
            (5, "новая", "закрыта", 4, "07.05.2026 15:40"),
            (6, None, "новая", 5, "21.05.2026 08:10"),
            (6, "новая", "в работе", 3, "21.05.2026 08:40"),
            (7, None, "новая", 2, "15.05.2026 10:05"),
            (8, None, "новая", 5, "18.04.2026 17:30"),
            (8, "новая", "закрыта", 3, "20.04.2026 09:15"),
            (9, None, "новая", 2, "09.05.2026 12:25"),
            (9, "новая", "ожидает ответа", 3, "10.05.2026 10:00"),
            (10, None, "новая", 6, "01.05.2026 07:50"),
            (10, "новая", "закрыта", 4, "01.05.2026 08:35"),
            (11, None, "новая", 6, "20.05.2026 14:55"),
            (12, None, "новая", 1, "06.05.2026 09:40"),
            (12, "новая", "в работе", 3, "06.05.2026 11:15"),
        ]
        connection.executemany(
            """
            INSERT INTO status_history (ticket_id, old_status, new_status, changed_by, changed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            history,
        )
