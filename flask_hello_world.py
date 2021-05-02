from flask import Flask

app = Flask(__name__)
#讓使用者可以來訪問我這個接口
@app.route('/')
def helloFlask():
    return 'Hello World!'
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)