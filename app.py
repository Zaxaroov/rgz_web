from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['DATABASE'] = 'dating_db.db'  # Используем SQLite базу данных

# Helper functions for SQLite database interaction
def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row  # To return rows as dictionaries
    return conn

def init_db():
    conn = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

# Models are now implemented via direct SQL queries in this example
# Create the database schema
@app.before_first_request
def create_tables():
    init_db()

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('profile'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        looking_for = request.form['looking_for']

        if not username or not password or not email or not name or not age or not gender or not looking_for:
            flash('All fields are required!')
            return redirect(url_for('register'))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            flash('Username already exists!')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, password, email, name, age, gender, looking_for) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (username, hashed_password, email, name, int(age), gender, looking_for))
        conn.commit()
        conn.close()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash('Login successful!')
            return redirect(url_for('profile'))
        else:
            flash('Invalid username or password.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        age = int(request.form['age'])
        gender = request.form['gender']
        looking_for = request.form['looking_for']
        about = request.form['about']
        hidden = 'hidden' in request.form

        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename:
                photo_path = os.path.join('static/uploads', photo.filename)
                photo.save(photo_path)
                cursor.execute("""
                    UPDATE users SET name = ?, age = ?, gender = ?, looking_for = ?, about = ?, hidden = ?, photo = ?
                    WHERE id = ?
                """, (name, age, gender, looking_for, about, hidden, photo_path, session['user_id']))
            else:
                cursor.execute("""
                    UPDATE users SET name = ?, age = ?, gender = ?, looking_for = ?, about = ?, hidden = ?
                    WHERE id = ?
                """, (name, age, gender, looking_for, about, hidden, session['user_id']))
        else:
            cursor.execute("""
                UPDATE users SET name = ?, age = ?, gender = ?, looking_for = ?, about = ?, hidden = ?
                WHERE id = ?
            """, (name, age, gender, looking_for, about, hidden, session['user_id']))

        conn.commit()
        conn.close()

        flash('Profile updated successfully!')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

@app.route('/search', methods=['GET'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    name_query = request.args.get('name', '')
    age_query = request.args.get('age', '')
    page = int(request.args.get('page', 1))

    query = "SELECT * FROM users WHERE hidden = 0 AND id != ? AND gender = (SELECT looking_for FROM users WHERE id = ?) AND looking_for = (SELECT gender FROM users WHERE id = ?)"
    params = [session['user_id'], session['user_id'], session['user_id']]

    if name_query:
        query += " AND name LIKE ?"
        params.append(f'%{name_query}%')
    if age_query.isdigit():
        query += " AND age = ?"
        params.append(int(age_query))

    cursor.execute(query, params)
    users = cursor.fetchall()
    conn.close()

    return render_template('search.html', users=users, name_query=name_query, age_query=age_query)

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (session['user_id'],))
    conn.commit()
    conn.close()

    session.pop('user_id', None)
    flash('Account deleted successfully.')
    return redirect(url_for('index'))

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
