from flask import *

app = Flask(__name__)

#@app.route("/login", methods=['POST'])
#def login():
#    print("Login")
#    return "Pressed"
	
@app.route('/', methods=['GET'])
def default():
    return render_template("index.html")
