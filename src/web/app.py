# from flask import Flask, render_template
#
# app = Flask(__name__)
#
#
# @app.route('/')
# def index():
#     return render_template('index.html', title='Signin')
#
#
# if __name__ == "__main__":
#     app.run(debug=True)
from src.web import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
