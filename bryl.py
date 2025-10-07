from flask  import Flask, render_template
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy

bryl = Flask(__name__)

@bryl.route("/")
def index():
    return render_template('index.html')

bryl.route("/")
def about():
    return render_template('about.html')


if __name__ == '__main__':
    bryl.run(debug=True)