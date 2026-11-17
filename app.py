import os
import json
import uuid
from flask import Flask, flash, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "temsalet_fc_ultra_secure_key"

AUTH_FILE = "owner_auth.json"
DATA_FILE = "club_data.json"
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_auth():
    if not os.path.exists(AUTH_FILE):
        return None
    with open(AUTH_FILE, "r") as f:
        return json.load(f)

def save_auth(username, password):
    with open(AUTH_FILE, "w") as f:
        json.dump({"username": username.strip(), "password": password.strip()}, f)

def get_data():
    default_coach = {
        "name": "Head Coach",
        "role": "Manager & Coach",
        "photo": "owner.jpg"
    }
    if not os.path.exists(DATA_FILE):
        default_data = {
            "coach": default_coach,
            "victories": [],
            "matches": [
                {"id": "1", "opp": "City Rivals", "score": "3 - 1", "date": "Nov 10, 2026", "status": "Finished"},
                {"id": "2", "opp": "United FC", "score": "VS", "date": "Nov 22, 2026", "status": "Upcoming"}
            ],
            "players": [
                {"id": "101", "name": "Yonas B.", "num": "10", "pos": "Forward"},
                {"id": "102", "name": "Alex Smith", "num": "1", "pos": "Goalkeeper"}
            ]
        }
        save_data(default_data)
        return default_data

    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    if "coach" not in data:
        data["coach"] = default_coach
    if "victories" not in data:
        data["victories"] = []
    return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# 1. PUBLIC WEBSITE
@app.route("/")
def home():
    data = get_data()
    finished = [m for m in data["matches"] if m["status"] == "Finished"]
    upcoming = [m for m in data["matches"] if m["status"] == "Upcoming"]
    return render_template(
        "index.html",
        coach=data["coach"],
        finished=finished,
        upcoming=upcoming,
        players=data["players"]
    )

# 2. CLUB VICTORIES GALLERY
@app.route("/victories")
def victories():
    data = get_data()
    return render_template("victories.html", victories=data["victories"])

# 3. FIRST-TIME SETUP & LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    auth = get_auth()
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not auth:
            if len(username) < 3 or len(password) < 4:
                error = "Username needs 3+ characters, password needs 4+ characters."
            else:
                save_auth(username, password)
                session["admin_logged_in"] = True
                return redirect(url_for("admin"))
        else:
            if username == auth["username"] and password == auth["password"]:
                session["admin_logged_in"] = True
                return redirect(url_for("admin"))
            else:
                error = "Wrong username or password!"

    return render_template("login.html", is_setup=(auth is None), error=error)

# 4. OWNER CONTROL PANEL
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    data = get_data()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_coach":
            data["coach"]["name"] = request.form.get("coach_name", "").strip() or data["coach"]["name"]
            data["coach"]["role"] = request.form.get("coach_role", "").strip() or data["coach"]["role"]

            file = request.files.get("coach_photo")
            if file and file.filename:
                ext = os.path.splitext(secure_filename(file.filename))[1].lower()
                if ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    filename = f"coach_{uuid.uuid4().hex[:8]}{ext}"
                    file.save(os.path.join(UPLOAD_FOLDER, filename))
                    data["coach"]["photo"] = f"uploads/{filename}"

        elif action == "add_victory":
            file = request.files.get("victory_photo")
            title = request.form.get("title", "").strip()
            date = request.form.get("date", "").strip()
            if not title or not date:
                flash("Enter a title and date for the victory photo.", "error")
            elif not file or not file.filename:
                flash("Choose a victory photo to upload.", "error")
            else:
                ext = os.path.splitext(secure_filename(file.filename))[1].lower()
                if ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    filename = f"victory_{uuid.uuid4().hex[:8]}{ext}"
                    file.save(os.path.join(UPLOAD_FOLDER, filename))
                    data["victories"].insert(0, {
                        "id": str(uuid.uuid4())[:8],
                        "title": title,
                        "date": date,
                        "photo": f"uploads/{filename}"
                    })
                    flash("Victory photo uploaded.", "success")
                else:
                    flash("Victory photos must be JPG, PNG, or WebP images.", "error")

        elif action == "delete_victory":
            v_id = request.form.get("victory_id")
            victory = next((v for v in data["victories"] if v.get("id") == v_id), None)
            if victory:
                photo = victory.get("photo", "")
                filename = os.path.basename(photo)
                if photo == f"uploads/{filename}" and filename:
                    photo_path = os.path.join(UPLOAD_FOLDER, filename)
                    if os.path.isfile(photo_path):
                        os.remove(photo_path)
                data["victories"] = [v for v in data["victories"] if v.get("id") != v_id]
                flash("Victory photo deleted.", "success")
            else:
                flash("Victory photo not found.", "error")

        elif action == "add_match":
            data["matches"].insert(0, {
                "id": str(uuid.uuid4())[:8],
                "opp": request.form.get("opp"),
                "score": request.form.get("score") or "VS",
                "date": request.form.get("date"),
                "status": request.form.get("status")
            })

        elif action == "edit_match":
            m_id = request.form.get("match_id")
            for m in data["matches"]:
                if m["id"] == m_id:
                    m["opp"] = request.form.get("opp")
                    m["score"] = request.form.get("score")
                    m["date"] = request.form.get("date")
                    m["status"] = request.form.get("status")
                    break

        elif action == "delete_match":
            m_id = request.form.get("match_id")
            data["matches"] = [m for m in data["matches"] if m["id"] != m_id]

        elif action == "add_player":
            data["players"].append({
                "id": str(uuid.uuid4())[:8],
                "name": request.form.get("name"),
                "num": request.form.get("num"),
                "pos": request.form.get("pos")
            })

        elif action == "delete_player":
            p_id = request.form.get("player_id")
            data["players"] = [p for p in data["players"] if p["id"] != p_id]

        elif action == "change_pass":
            new_u = request.form.get("new_username", "").strip()
            new_p = request.form.get("new_password", "").strip()
            if len(new_u) >= 3 and len(new_p) >= 4:
                save_auth(new_u, new_p)

        save_data(data)
        return redirect(url_for("admin"))

    return render_template(
        "admin.html",
        coach=data["coach"],
        victories=data["victories"],
        matches=data["matches"],
        players=data["players"],
        auth=get_auth()
    )

# 5. LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)