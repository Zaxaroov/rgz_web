from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Инициализация приложения
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  

# Создание Blueprint
rgz = Blueprint('rgz', __name__, url_prefix='/rgz')

# Функции для работы с базой данных
def db_connect():
    try:
        conn = psycopg2.connect(
            host='127.0.0.1',
            database='zaxarov_ilya_knowledge_base',
            user='zaxarov_ilya_knowledge_base',
            password='123'
        )
        return conn, conn.cursor(cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return None, None

def db_close(conn, cur):
    if cur: cur.close()
    if conn: conn.close()

# Главная страница
@rgz.route('/')
def main():
    return render_template('rgz.html')

# Регистрация
@rgz.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Получаем данные из формы
        data = {key: request.form.get(key) for key in ['Имя пользователя', 'Пароль', 'email', 'Имя', 'Возраст', 'Пол', 'Я ищу', 'Обо мне']}
        
        # Проверяем заполнение всех полей (поле "Обо мне" не обязательно, можно оставить пустым)
        if not all(value for key, value in data.items() if key != 'Обо мне'):
            flash('Все обязательные поля должны быть заполнены!')
            return redirect(url_for('rgz.register'))

        conn, cur = db_connect()
        if not conn:
            flash("Ошибка подключения к базе данных.")
            return redirect(url_for('rgz.register'))

        try:
            # Проверяем существование пользователя
            cur.execute("SELECT id FROM usersi WHERE username = %s", (data['Имя пользователя'],))
            if cur.fetchone():
                flash('Этот ник занят!')
                return redirect(url_for('rgz.register'))

            # Хешируем пароль и добавляем пользователя
            hashed_password = generate_password_hash(data['Пароль'])
            cur.execute("""
                INSERT INTO usersi (username, password, email, name, age, gender, looking_for, about) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (data['Имя пользователя'], hashed_password, data['email'], data['Имя'], int(data['Возраст']), data['Пол'], data['Я ищу'], data['Обо мне'] or ''))
            conn.commit()

            flash('Регистрация прошла успешно!')
            return redirect(url_for('rgz.success', username=data['Имя пользователя']))
        except Exception as e:
            print(f"Ошибка регистрации: {e}")
            flash("Ошибка регистрации. Попробуйте позже.")
        finally:
            db_close(conn, cur)

    return render_template('register.html')


# Успешная регистрация
@rgz.route('/success/')
def success():
    username = request.args.get('username', 'пользователь')
    return render_template('success.html', username=username)

# Авторизация
@rgz.route('/rgz/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('Имя пользователя')
        password = request.form.get('Пароль')

        conn, cur = db_connect()
        if not conn:
            flash("Ошибка подключения к базе данных.")
            return redirect(url_for('rgz.login'))

        try:
            cur.execute("SELECT * FROM usersi WHERE username = %s", (username,))
            user = cur.fetchone()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                flash('Вы успешно вошли!')
                return redirect(url_for('rgz.profile'))
            else:
                flash('Неверное имя пользователя или пароль.')
        except Exception as e:
            print(f"Ошибка авторизации: {e}")
            flash("Ошибка авторизации. Попробуйте позже.")
        finally:
            db_close(conn, cur)

    return render_template('login.html')

# Профиль пользователя
@rgz.route('/profile/', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Сначала выполните вход.')
        return redirect(url_for('rgz.login'))

    conn, cur = db_connect()
    if not conn:
        flash("Ошибка подключения к базе данных.")
        return redirect(url_for('rgz.login'))

    try:
        # Получаем текущие данные пользователя
        cur.execute("SELECT * FROM usersi WHERE id = %s", (session['user_id'],))
        user = cur.fetchone()

        if request.method == 'POST':
            # Обновляем данные пользователя
            updates = {key: request.form.get(key) for key in ['Имя', 'Возраст', 'Пол', 'Я ищу', 'Обо мне']}
            hidden = 'hidden' in request.form
            photo = request.files.get('Фото')

            # Сохранение фото, если загружено
            photo_path = user['photo']  # Текущий путь к фото
            if photo and photo.filename:
                photo_path = os.path.join('static/uploads', photo.filename)
                photo.save(photo_path)

            # Обновляем данные в базе
            cur.execute("""
                UPDATE usersi 
                SET name = %s, age = %s, gender = %s, looking_for = %s, about = %s, hidden = %s, photo = %s
                WHERE id = %s
            """, (updates['Имя'], int(updates['Возраст']), updates['Пол'], updates['Я ищу'], updates['Обо мне'], hidden, photo_path, session['user_id']))
            conn.commit()
            flash('Профиль обновлен!')
            return redirect(url_for('rgz.profile'))
    except Exception as e:
        print(f"Ошибка при обновлении профиля: {e}")
        flash("Ошибка загрузки профиля.")
    finally:
        db_close(conn, cur)

    return render_template('profile.html', user=user)


# Выход из аккаунта
@rgz.route('/logout/')
def logout():
    session.pop('user_id', None)
    flash('Вы успешно вышли из аккаунта.')
    return redirect(url_for('rgz.login'))

# Удаление аккаунта
@rgz.route('/delete_account/', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        flash('Сначала выполните вход.')
        return redirect(url_for('rgz.login'))

    conn, cur = db_connect()
    if not conn:
        flash("Ошибка подключения к базе данных.")
        return redirect(url_for('rgz.profile'))

    try:
        # Удаляем пользователя из базы данных
        cur.execute("DELETE FROM usersi WHERE id = %s", (session['user_id'],))
        conn.commit()
        session.pop('user_id', None)  # Удаляем данные сессии
        flash('Ваш аккаунт был успешно удален.')
        return redirect(url_for('rgz.register'))
    except Exception as e:
        print(f"Ошибка при удалении аккаунта: {e}")
        flash("Ошибка при удалении аккаунта. Попробуйте позже.")
    finally:
        db_close(conn, cur)


@rgz.route('/search', methods=['GET', 'POST'])
def search():
    if 'user_id' not in session:
        flash('Сначала выполните вход.')
        return redirect(url_for('rgz.login'))

    conn, cur = db_connect()
    if not conn:
        flash("Ошибка подключения к базе данных.")
        return redirect(url_for('rgz.profile'))

    try:
        # Получаем текущего пользователя
        cur.execute("SELECT * FROM usersi WHERE id = %s", (session['user_id'],))
        current_user = cur.fetchone()

        if not current_user:
            flash('Пользователь не найден.')
            return redirect(url_for('rgz.profile'))

        # Получаем параметры фильтрации
        looking_for = request.args.get('looking_for', current_user['looking_for'])
        min_age = request.args.get('min_age', 18)  # Значение по умолчанию
        max_age = request.args.get('max_age', 25)  # Значение по умолчанию

        # Формируем запрос
        query = """
            SELECT * FROM usersi 
            WHERE id != %s 
              AND hidden = 0 
              AND gender = %s 
              AND age BETWEEN %s AND %s
            ORDER BY id
        """
        params = (current_user['id'], looking_for, min_age, max_age)

        # Выполняем запрос
        cur.execute(query, params)
        search_results = cur.fetchall()

    except Exception as e:
        print(f"Ошибка поиска: {e}")
        flash("Ошибка поиска. Попробуйте позже.")
        search_results = []
    finally:
        db_close(conn, cur)

    return render_template(
        'search.html', 
        users=search_results, 
        looking_for=looking_for, 
        min_age=min_age, 
        max_age=max_age
    )


    


# Регистрация Blueprint
app.register_blueprint(rgz)

# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True)
