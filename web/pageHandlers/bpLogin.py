from flask import render_template, Blueprint, flash, redirect, url_for, session
from flask_wtf import FlaskForm
# from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length
from utils.dbDeb import checkPass

bpLogin = Blueprint("Login_4Rapp", __name__)


class Loginform(FlaskForm):   # create our own form inherited from Flaskform
    username = StringField(label="Username",
                           validators=[DataRequired("UserNmae is required"),
                                       Length(min=4, max=15,
                                              message="Username must be between 3 to 15 characters")])
    password = PasswordField(label="Password",
                             validators=[DataRequired("Password is required"),
                                         Length(min=8, max=15,
                                                message="Username must be between 8 to 15 characters")])
    submit = SubmitField('Sign In')


@bpLogin.route("/", methods=["GET", "POST"])
def login():
    form = Loginform()
    if form.validate_on_submit():
        # ----- can get userid and password to check against database here ----
        loginuser = form.username.data
        loginPass = form.password.data
        # -------- validate against database, if not, return error
        match = checkPass(loginuser, loginPass)
        if match and match['passmatched']:
            session["user"] = loginuser         # keep user in session variable
            return redirect(url_for('Index_blueprint.index'))
        else:
            flash("UserID or Password is incorrect")
    # debug only
    # print(form.validate())
    # print(form.errors)
    return render_template('login.html', title='Sign In', form=form)
