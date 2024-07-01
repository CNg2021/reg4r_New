from flask import Blueprint, request, render_template, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length
from utils.dbDeb import Lookupclient, updateAllQrcodes, getClientAttendance
from utils.genNameTagDoc import genNameTagDoc

bpFindClient = Blueprint('LookupClient_blueprint', __name__)


class dbUtilForm(FlaskForm):
    submitUpdateQR = SubmitField('Update all QRCodes')
    submitMakeNameTags = SubmitField('Make all name tags')


# -------------- put a search bar in order to find existing client and update info ------------
class searchClientForm(FlaskForm):
    firstName = StringField(label="First Name",
                            validators=[Length(min=2, max=25,
                                               message="first name must be at least 2 characters")])

    lastName = StringField(label="Last Name",
                           validators=[Length(min=2, max=25,
                                              message="last name must be at least 2 characters")])

    phoneNumber = StringField(label="Phone number", id="phone",
                              validators=[Length(min=10, max=15,
                                                 message="Phone number must be 10 to 15 characters")])

    submitSearch = SubmitField('Search')


@bpFindClient.route("/searchClient", methods=["POST", "GET"])
def searchClient():
    formUtil = dbUtilForm()     # piggy back form
    form = searchClientForm()
    records = None
    tblAttendance = None
    todo = None
    showAdminUtil = False
    if session['user'] == 'Chester':
        showAdminUtil = True

    if request.method == "POST":
        todo = request.form['todo']
        if todo == '':
            if form.submitSearch.data and form.is_submitted:
                if not form.phoneNumber.data and not form.lastName.data and not form.firstName.data:
                    flash("Please enter at least 1 search Criteria")
                else:
                    records = Lookupclient(form.firstName.data, form.lastName.data, form.phoneNumber.data)
        if todo == 'clientAttendance':
            clientID = request.form['clientID']    # in case it's posting client id
            tblAttendance = getClientAttendance(clientID)

        if formUtil.submitUpdateQR.data and formUtil.is_submitted:
            try:
                updateAllQrcodes()
                flash("updated all QR codes")
            except Exception as error:
                err = f"updateAllQrcodes() error occured:{error}"
                print(err)
                print("Exception type:", type(error))
                flash(Exception(err))

        if formUtil.submitMakeNameTags.data and formUtil.is_submitted:
            try:
                genNameTagDoc()
                flash("Name Tags are done")
            except Exception as error:
                err = f"genNameTagDoc() error occured:{error}"
                print(err)
                print("Exception type:", type(error))
                flash(Exception(err))

    return render_template("searchClient.html",
                           form=form,
                           formUtil=formUtil,
                           showAdmin=showAdminUtil,
                           clients=records,
                           tblAttendance=tblAttendance)
