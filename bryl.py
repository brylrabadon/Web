from flask import Flask, render_template

bryl = Flask(__name__)

@bryl.route("/")
def index():
    return render_template('index.html')

@bryl.route("/about")
def about():
    return render_template('about.html')

@bryl.route("/contact")
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    bryl.run(debug=True)
