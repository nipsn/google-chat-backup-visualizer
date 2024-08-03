from flask import Flask, current_app

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return current_app.send_static_file('index.html')


if __name__ == '__main__':
    app.run()
