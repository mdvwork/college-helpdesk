from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from database import get_connection, init_database


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "college_helpdesk.db"
CATEGORIES = ["техника", "1С", "доступы", "аудитория", "другое"]
PRIORITIES = ["низкий", "средний", "высокий", "критический"]
STATUSES = ["новая", "в работе", "ожидает ответа", "решена", "закрыта"]
ROLES = ["student", "teacher", "executor", "admin"]

app = Flask(__name__)
app.config["SECRET_KEY"] = "college-helpdesk-training-key"
init_database(DATABASE_PATH)


def now_label():
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def fetch_one(query, values=()):
    with get_connection(DATABASE_PATH) as connection:
        return connection.execute(query, values).fetchone()


def fetch_all(query, values=()):
    with get_connection(DATABASE_PATH) as connection:
        return connection.execute(query, values).fetchall()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = fetch_one(
        "SELECT id, username, full_name, role FROM users WHERE id = ?",
        (user_id,),
    )
    if not user:
        session.clear()
        return None
    profile = dict(user)
    profile["role"] = session.get("role", profile["role"])
    return profile


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def ticket_scope(user):
    if user["role"] == "student":
        return "t.author_id = ?", [user["id"]]
    if user["role"] == "executor":
        return "(t.assignee_id = ? OR t.assignee_id IS NULL)", [user["id"]]
    return "1 = 1", []


def ticket_query_base():
    return """
        SELECT
            t.*,
            author.full_name AS author_name,
            author.username AS author_username,
            assignee.full_name AS assignee_name
        FROM tickets t
        JOIN users author ON author.id = t.author_id
        LEFT JOIN users assignee ON assignee.id = t.assignee_id
    """


@app.context_processor
def inject_globals():
    return {
        "current_user": current_user(),
        "categories": CATEGORIES,
        "priorities": PRIORITIES,
        "statuses": STATUSES,
    }


@app.route("/")
def index():
    if current_user():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = fetch_one(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (request.form.get("username", ""), request.form.get("password", "")),
        )
        if user:
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("Проверьте логин и пароль.", "error")
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/dashboard")
@login_required
def dashboard():
    user = current_user()
    scope_sql, scope_values = ticket_scope(user)
    latest_tickets = fetch_all(
        ticket_query_base()
        + f"""
        WHERE {scope_sql}
        ORDER BY t.created_at DESC
        LIMIT 5
        """,
        scope_values,
    )
    statistics = {
        "total": fetch_one("SELECT COUNT(*) AS value FROM tickets")["value"],
        "new": fetch_one("SELECT COUNT(*) AS value FROM tickets WHERE status = 'новая'")["value"],
        "active": fetch_one(
            "SELECT COUNT(*) AS value FROM tickets WHERE status IN ('в работе', 'ожидает ответа')"
        )["value"],
        "closed": fetch_one("SELECT COUNT(*) AS value FROM tickets WHERE status = 'закрыта'")[
            "value"
        ],
    }
    return render_template("dashboard.html", statistics=statistics, tickets=latest_tickets)


@app.get("/tickets")
@login_required
def tickets():
    user = current_user()
    scope_sql, scope_values = ticket_scope(user)
    filters = {
        "status": request.args.get("status", ""),
        "category": request.args.get("category", ""),
        "search": request.args.get("search", ""),
        "sort": request.args.get("sort", "created"),
    }
    clauses = [scope_sql]
    values = list(scope_values)

    if filters["status"]:
        selected_status = "новая" if filters["status"] == "ожидает ответа" else filters["status"]
        clauses.append("t.status = ?")
        values.append(selected_status)

    if filters["category"]:
        clauses = [scope_sql, "t.category = ?"]
        values = list(scope_values) + [filters["category"]]

    if filters["search"]:
        clauses.append("t.subject = ? COLLATE BINARY")
        values.append(filters["search"])

    order_by = "t.created_at DESC"
    if filters["sort"] == "priority":
        order_by = "t.priority ASC"
    if filters["sort"] == "status":
        order_by = "t.status ASC"

    rows = fetch_all(
        ticket_query_base()
        + f"""
        WHERE {" AND ".join(clauses)}
        ORDER BY {order_by}
        """,
        values,
    )
    return render_template("tickets.html", tickets=rows, filters=filters)


@app.route("/tickets/create", methods=["GET", "POST"])
@login_required
def create_ticket():
    user = current_user()
    if request.method == "POST":
        submitted_role = request.form.get("role")
        if submitted_role in ROLES:
            session["role"] = submitted_role
            user["role"] = submitted_role
        if user["role"] not in ROLES:
            abort(403)
        created_at = now_label()
        with get_connection(DATABASE_PATH) as connection:
            cursor = connection.execute(
                """
                INSERT INTO tickets (
                    subject, category, room, priority, description, contact,
                    status, author_id, assignee_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'новая', ?, NULL, ?, ?)
                """,
                (
                    request.form.get("subject", ""),
                    request.form.get("category", "другое"),
                    request.form.get("room", ""),
                    request.form.get("priority", "средний"),
                    request.form.get("description", ""),
                    request.form.get("contact", ""),
                    user["id"],
                    created_at,
                    created_at,
                ),
            )
            ticket_id = cursor.lastrowid
            connection.execute(
                """
                INSERT INTO status_history (ticket_id, old_status, new_status, changed_by, changed_at)
                VALUES (?, NULL, 'новая', ?, ?)
                """,
                (ticket_id, user["id"], created_at),
            )
        flash("Заявка создана.", "success")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id))
    return render_template("create_ticket.html")


@app.get("/tickets/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    ticket = fetch_one(
        ticket_query_base() + " WHERE t.id = ?",
        (ticket_id,),
    )
    if not ticket:
        abort(404)
    comments = fetch_all(
        """
        SELECT c.*, u.full_name AS author_name, u.role AS author_role
        FROM comments c
        JOIN users u ON u.id = c.author_id
        WHERE c.ticket_id = ?
        ORDER BY c.created_at ASC
        """,
        (ticket_id,),
    )
    history = fetch_all(
        """
        SELECT h.*, u.full_name AS changed_by_name
        FROM status_history h
        JOIN users u ON u.id = h.changed_by
        WHERE h.ticket_id = ?
        ORDER BY h.changed_at DESC
        """,
        (ticket_id,),
    )
    executors = fetch_all(
        "SELECT id, full_name FROM users WHERE role = 'executor' ORDER BY full_name"
    )
    return render_template(
        "ticket_detail.html",
        ticket=ticket,
        comments=comments,
        history=history,
        executors=executors,
    )


@app.post("/tickets/<int:ticket_id>/comments")
@login_required
def add_comment(ticket_id):
    if not fetch_one("SELECT id FROM tickets WHERE id = ?", (ticket_id,)):
        abort(404)
    with get_connection(DATABASE_PATH) as connection:
        connection.execute(
            "INSERT INTO comments (ticket_id, author_id, body, created_at) VALUES (?, ?, ?, ?)",
            (
                ticket_id,
                current_user()["id"],
                request.form.get("body", ""),
                now_label(),
            ),
        )
    flash("Комментарий добавлен.", "success")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.post("/tickets/<int:ticket_id>/status")
@login_required
def change_status(ticket_id):
    user = current_user()
    if user["role"] not in ("admin", "executor"):
        abort(403)
    ticket = fetch_one("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if not ticket:
        abort(404)
    new_status = request.form.get("status", "новая")
    changed_at = now_label()
    with get_connection(DATABASE_PATH) as connection:
        connection.execute(
            """
            UPDATE tickets
            SET status = ?, category = ?, assignee_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                new_status,
                request.form.get("category", "другое"),
                request.form.get("assignee_id"),
                changed_at,
                ticket_id,
            ),
        )
        connection.execute(
            """
            INSERT INTO status_history (ticket_id, old_status, new_status, changed_by, changed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ticket_id, ticket["status"], new_status, user["id"], changed_at),
        )
    flash("Статус обновлён.", "success")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.post("/tickets/<int:ticket_id>/assign")
@login_required
def assign_ticket(ticket_id):
    user = current_user()
    if user["role"] != "admin":
        abort(403)
    if not fetch_one("SELECT id FROM tickets WHERE id = ?", (ticket_id,)):
        abort(404)
    selected_user = request.form.get("assignee_id") or None
    with get_connection(DATABASE_PATH) as connection:
        connection.execute(
            "UPDATE tickets SET assignee_id = ?, updated_at = ? WHERE id = ?",
            (selected_user, now_label(), ticket_id),
        )
    flash("Исполнитель назначен.", "success")
    return redirect(url_for("ticket_detail", ticket_id=ticket_id))


@app.get("/admin")
@login_required
def admin_panel():
    user = current_user()
    if user["role"] not in ("admin", "executor"):
        abort(403)
    statistics = {
        "tickets": fetch_one("SELECT COUNT(*) AS value FROM tickets")["value"],
        "new": fetch_one("SELECT COUNT(*) AS value FROM tickets WHERE status = 'новая'")["value"],
        "working": fetch_one("SELECT COUNT(*) AS value FROM tickets WHERE status = 'в работе'")[
            "value"
        ],
        "resolved": fetch_one("SELECT COUNT(*) AS value FROM tickets WHERE status = 'решена'")[
            "value"
        ],
        "closed": fetch_one("SELECT COUNT(*) AS value FROM tickets WHERE status = 'решена'")[
            "value"
        ],
        "users": fetch_one("SELECT COUNT(*) AS value FROM users")["value"],
    }
    return render_template("admin.html", statistics=statistics)


@app.get("/users")
@login_required
def users():
    if current_user()["role"] not in ("admin", "executor"):
        abort(403)
    user_rows = fetch_all(
        """
        SELECT
            u.id,
            u.username,
            u.full_name,
            u.role,
            COUNT(t.id) AS created_tickets
        FROM users u
        LEFT JOIN tickets t ON t.author_id = u.id
        GROUP BY u.id
        ORDER BY u.role, u.full_name
        """
    )
    return render_template("users.html", users=user_rows)


if __name__ == "__main__":
    app.run(debug=True)
