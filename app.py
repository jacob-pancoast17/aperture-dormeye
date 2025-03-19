from flask import *

app = Flask(__name__)
	
@app.route('/', methods=['GET'])
def default():
    return render_template("index.html")
