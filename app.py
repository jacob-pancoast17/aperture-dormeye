from face_recognition_app.facial_recognition import generate_frames
from flask import *
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import FileField, PasswordField, StringField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ca258998190a853b6a12d1133e083a7463e25f260738307e617560b98394dce3'
app.config['UPLOAD_FOLDER'] = 'static/files'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/pi/Desktop/aperture-dormeye/database.db' # Connects app to the database
db = SQLAlchemy(app) # Creates database
bcrypt = Bcrypt(app)

# Creates the "upload" button for users to upload face files
class UploadFileForm(FlaskForm):
    file = FileField("File", validators=[InputRequired()])
    submit = SubmitField("Upload File")

# Represents a User in the database, with an id, a unique username, and a password
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
                usernam=username.data).first()

        if existing_user_username:
            raise ValidationError(
                    "That username already exists. Please choose a different one.")

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")
	
@app.route('/', methods=["GET", "POST"])
def default():
    return render_template("index.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    return render_template("login.html", form=form)

@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.gene rate_password_has(form.password.data)
        new_user = User(form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
    return render_template("register.html", form=form)

@app.route('/main', methods=["GET", "POST"])
def main():
    form = UploadFileForm()
    if form.validate_on_submit():
        file = form.file.data # Store the file in a variable
        file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'], secure_filename(file.filename))) # Save the file
        return render_template("main.html", form=form)
    return render_template("main.html", form=form)

@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0.', port=5000, debug=True, threaded=True)


