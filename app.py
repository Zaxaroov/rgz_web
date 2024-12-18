from flask import Flask, redirect, url_for, render_template
from rgz import rgz
import os

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'секретно-секретный секрет') 
app.config['DB_TYPE'] = os.getenv('DB_TYPE', 'postgres')

app.register_blueprint(rgz)



@app.route("/")
@app.route("/index")
def start():
    return redirect("/menu", code=302)

@app.route("/menu")
def menu():
    return '''
<!DOCTYPE html>
<html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="''' + url_for('static', filename='main.css') + '''">
        <title>Захаров Илья Максимович</title>
    </head>
    <body>
        <header>
            НГТУ, ФБ, WEB-программирование, часть 2. РГЗ
        </header>
        
        <div>
                <li>
                    <a href="/rgz">расчетно-графическое задание</a>
                </li>
            </ol>
        </div>

        <footer class="footer">
            &copy; Захаров Илья, ФБИ-24, 3 курс, 2024 
        </footer>
    </body>
</html>
'''