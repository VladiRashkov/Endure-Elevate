from flask import Flask, redirect, session
from src.routers.user import user_routes
from src.routers.token import token_routes
from src.routers.activity import activity_routes
from src.routers.calculator import calculator_router


app = Flask(__name__)
app.secret_key = 'b7c6dGtv931F3n89MsoZKJp394ksOdpz'

app.register_blueprint(user_routes, url_prefix='/user')
app.register_blueprint(token_routes)
app.register_blueprint(activity_routes)
app.register_blueprint(calculator_router, url_prefix="/")


@app.route('/')
def home():
    return redirect('/user/register')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)


