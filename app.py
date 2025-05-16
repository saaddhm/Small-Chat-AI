from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_bcrypt import Bcrypt
import google.generativeai as genai
import config

app = Flask(__name__)
app.config.from_object(config)

# Extensions
mysql = MySQL(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Gemini AI
genai.configure(api_key="")
model = genai.GenerativeModel("gemini-2.0-flash")

# User class
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username FROM users WHERE id=%s", (user_id,))
    data = cur.fetchone()
    cur.close()
    if data:
        return User(id=data[0], username=data[1])
    return None

# Routes
@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, password_hash FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user[1], password):
            login_user(User(id=user[0], username=username))
            return redirect(url_for('index'))
        return "Identifiants invalides", 401
    return render_template('login.html')
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("insert into users (username, password_hash) values (%s, %s)", (username, bcrypt.generate_password_hash(password)))
        mysql.connection.commit()
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user[1], password):
            login_user(User(id=user[0], username=username))
            return redirect(url_for('index'))
        return "Identifiants invalides", 401
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    user_input = request.json['message']
    response = model.start_chat().send_message(user_input).text

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO messages (user_id, sender, message) VALUES (%s, %s, %s)", (current_user.id, 'user', user_input))
    cur.execute("INSERT INTO messages (user_id, sender, message) VALUES (%s, %s, %s)", (current_user.id, 'ai', response))
    mysql.connection.commit()
    cur.close()

    return jsonify({'response': response})
@app.route('/messages')
@login_required
def get_messages():
    cur = mysql.connection.cursor()
    cur.execute("SELECT sender, message FROM messages WHERE user_id = %s", (current_user.id,))
    messages = cur.fetchall()
    cur.close()
    return jsonify([{'sender': row[0], 'message': row[1]} for row in messages])

if __name__ == '__main__':
    app.run(debug=True)
