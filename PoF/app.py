from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from pof import PoF


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
pof = PoF(app, dedicated_route="/pof")


@app.route("/")
@pof.protect()
def index():
    """
    Protect against bots and DDoS attacks.
    """
    return "Hello, Human!"


@app.route("/protected")
def protected():
    """
    Protect against bots and DDoS attacks.
    """
    if not pof.is_verified:
        return pof.challenge()
    return "Hello, Human!"


if __name__ == "__main__":
    app.run(debug=True)
