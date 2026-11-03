from flask import Flask, request, render_template, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection

app = Flask(__name__)
app.secret_key = "taskflow-secret-key"

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") == "admin":
        return redirect("/admin")

    return render_template(
        "dashboard.html",
        username=session.get("username")
    )
@app.route("/register")
def register_page():
    return render_template("register.html")
@app.route("/login")
def login_page():
    return render_template("login.html")
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
@app.route("/admin")
def admin_page():
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        return redirect("/dashboard")

    return render_template("admin.html")
@app.route("/my-requests")
def my_requests():
    return render_template("my_requests.html")
@app.route("/api/my-requests", methods=["GET"])
def get_my_requests():
    user_id = session.get("user_id")

    if user_id is None:
        return {"message": "Please login first"}, 401

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            r.id,
            c.name AS category,
            r.title,
            r.description,
            r.priority,
            r.status,
            r.created_at
        FROM requests r
        JOIN categories c ON r.category_id = c.id
        WHERE r.user_id = %s
        ORDER BY r.id DESC
        """,
        (user_id,)
    )

    requests = cursor.fetchall()

    cursor.close()
    connection.close()

    result = []

    for item in requests:
        result.append({
            "id": item[0],
            "category": item[1],
            "title": item[2],
            "description": item[3],
            "priority": item[4],
            "status": item[5],
            "created_at": str(item[6])
        })

    return result
@app.route("/create-request")
def create_request_page():
    return render_template("create_request.html")

@app.route("/")
def home():
    return "TaskFlow backend is running!"


@app.route("/register", methods=["POST"])
def register():
    data = request.json

    username = data["username"]
    email = data["email"]
    password = data["password"]
    password_hash = generate_password_hash(password)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO users (username, email, password, role)
        VALUES (%s, %s, %s, %s)
        """,
        (username, email, password_hash, "user")
    )

    connection.commit()

    cursor.close()
    connection.close()

    return {"message": "User registered successfully!"}

@app.route("/login", methods=["POST"])
def login():
    data = request.json

    email = data["email"]
    password = data["password"]

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, username, password, role
        FROM users
        WHERE email = %s
        """,
        (email,)
    )

    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if user is None:
        return {"message": "User not found"}, 404

    if not check_password_hash(user[2], password):
        return {"message": "Incorrect password"}, 401
    session["user_id"] = user[0]
    session["username"] = user[1]
    session["role"] = user[3]
    return {
        "message": "Login successful!",
        "user_id": user[0],
        "username": user[1],
        "role": user[3]
    }
@app.route("/requests", methods=["POST"])
def create_request():
    data = request.json

    user_id = session.get("user_id")

    if user_id is None:
           return {"message": "Please login first"}, 401
    category_id = data["category_id"]
    title = data["title"]
    description = data["description"]
    priority = data["priority"]

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO requests
        (user_id, category_id, title, description, priority, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            user_id,
            category_id,
            title,
            description,
            priority,
            "New"
        )
    )

    request_id = cursor.fetchone()[0]

    connection.commit()

    cursor.close()
    connection.close()

    return {
        "message": "Request created successfully!",
        "request_id": request_id
    }, 201
@app.route("/requests", methods=["GET"])
def get_requests():
    if "user_id" not in session:
        return {"message": "Please login first"}, 401

    if session.get("role") != "admin":
        return {"message": "Access denied"}, 403
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            r.id,
            u.username,
            c.name AS category,
            r.title,
            r.description,
            r.priority,
            r.status,
            r.created_at
        FROM requests r
        JOIN users u ON r.user_id = u.id
        JOIN categories c ON r.category_id = c.id
        ORDER BY r.id DESC
        """
    )

    requests = cursor.fetchall()

    cursor.close()
    connection.close()

    result = []

    for item in requests:
        result.append({
            "id": item[0],
            "username": item[1],
            "category": item[2],
            "title": item[3],
            "description": item[4],
            "priority": item[5],
            "status": item[6],
            "created_at": str(item[7])
        })

    return result

@app.route("/requests/<int:request_id>/status", methods=["PUT"])
def update_status(request_id):
    if "user_id" not in session:
        return {"message": "Please login first"}, 401

    if session.get("role") != "admin":
        return {"message": "Access denied"}, 403
    data = request.json
    status = data["status"]

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE requests
        SET status = %s
        WHERE id = %s
        RETURNING id
        """,
        (status, request_id)
    )

    updated = cursor.fetchone()

    connection.commit()

    cursor.close()
    connection.close()

    if updated is None:
        return {"message": "Request not found"}, 404

    return {"message": "Status updated successfully!"}
@app.route("/dashboard/stats", methods=["GET"])
def dashboard_stats():
    if "user_id" not in session:
        return {"message": "Please login first"}, 401

    connection = get_connection()
    cursor = connection.cursor()

    if session.get("role") == "admin":
        cursor.execute("""
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE status = 'New'),
                COUNT(*) FILTER (WHERE status = 'In Progress'),
                COUNT(*) FILTER (WHERE status = 'Completed')
            FROM requests
        """)
    else:
        cursor.execute("""
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE status = 'New'),
                COUNT(*) FILTER (WHERE status = 'In Progress'),
                COUNT(*) FILTER (WHERE status = 'Completed')
            FROM requests
            WHERE user_id = %s
        """, (session["user_id"],))

    stats = cursor.fetchone()

    cursor.close()
    connection.close()

    return {
        "total": stats[0],
        "new": stats[1],
        "in_progress": stats[2],
        "completed": stats[3]
    }
if __name__ == "__main__":
    app.run(debug=True)