from flask import Blueprint, render_template, request, flash
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, HiddenField
from wtforms.validators import Length
from datetime import datetime
from utils.dbDeb import addAttendee, removeAttendee, getAllCurAttendees, getCurrentSessionID, Lookupclient
from time import sleep

# --- declare our attendance blueprint for handling the attendace request ---
bpAttendance = Blueprint("attendance_blueprint", __name__)


class sessionForm(FlaskForm):
    sessionID = HiddenField("sessionID")
    sessionDate = StringField("Create a session")
    sessionType = SelectField("session time", choices=[(0, "Morning"), (1, "Afternoon"), (2, "Evening")])
    firstName = StringField(label="FName",
                            validators=[Length(min=2, max=25,
                                               message="first name must be at least 2 characters")],
                            render_kw={"placeholder": "first name"}
                            )
    lastName = StringField(label="LName",
                           validators=[Length(min=2, max=25,
                                              message="last name must be at least 2 characters")],
                           render_kw={"placeholder": "last name"}
                           )
    phoneNumber = StringField(label="Phone number", id="phone",
                              validators=[Length(min=10, max=15,
                                                 message="Phone number must be 10 to 15 characters")],
                              render_kw={"placeholder": "phone number"}
                              )


@bpAttendance.route('/attendance', methods=["GET", "POST"])
def attendance():

    frmSession = sessionForm(request.form)
    # ------------ if loading form, default to current date and session type --------
    curAttendees = None
    records = None
    attend4R = tblLabel = ""
    if request.method == "GET":
        frmSession.sessionID.data = None
        dt = datetime.now().replace(second=0, microsecond=0)
        today = dt.date()
        timeNow = dt.time()
        sessionType = 0
        if timeNow.hour < 12:
            sessionType = 0
        elif timeNow.hour < 18:
            sessionType = 1
        else:
            sessionType = 2
        # get date in format of : Textual month, day and year
        today = datetime.today()
        d2 = today.strftime("%Y-%m-%d")
        frmSession.sessionDate.data = d2
        frmSession.sessionType.data = sessionType
        attend4R = "DMBC 4R Attendees -   " + d2
    # sessionID = getCurrentSessionID()
    elif request.method == "POST":
        clientID = request.form['clientIDtoAdd']    # in case it's posting client id
        todo = request.form['todo']                 # find out what we should be doing

        # ------------- first we check if we are dealing with session creation -----
        if todo == "createNewSession":  # --- if  create one ----
            sessionID = getCurrentSessionID(frmSession.sessionDate.data, frmSession.sessionType.data)
            if sessionID:
                frmSession.sessionID.data = sessionID
                frmSession.phoneNumber.data = frmSession.firstName.data = frmSession.lastName.data = ''
        # -------- next we check if we are dealing with looking up a client ------------
        elif not clientID and todo == "findClient":
            if not frmSession.phoneNumber.data and not frmSession.lastName.data and not frmSession.firstName.data:
                flash("Please enter at least 1 search Criteria")
            else:
                records = Lookupclient(frmSession.firstName.data, frmSession.lastName.data, frmSession.phoneNumber.data)
        # ----- if we locate a client and wants to add him to current session ----------
        elif clientID and todo == 'addClient':
            retCode = addAttendee(clientID, frmSession.sessionID.data)
            if retCode == 0:
                frmSession.phoneNumber.data = frmSession.firstName.data = frmSession.lastName.data = ''
        elif clientID and todo == 'removeClient':
            retCode = removeAttendee(clientID, frmSession.sessionID.data)

        # ------------------------------------------------------------------------------
        #  this session always activates if we hav a session ID, operator may use
        #  scanner to scan user qrcode and add him/her
        if frmSession.sessionID.data:
            scandata = request.form["qrcode"]
            if scandata is not None and isinstance(scandata, str):
                print(f"got data {scandata}")
                # ---- now that we get the data, parse and send over to addAttendance
                # the scan data is like this: DMBC4R 0003 KITTY WONG 416-222-1110
                datalist = scandata.split()
                if isinstance(datalist, list) and datalist.count(0) > 0 and datalist[0] == "DMBC4R":    # only if it is the right data
                    retCode = addAttendee(datalist[1], frmSession.sessionID.data)

                # ----------- get all current attenddees and show them -----------------
            curAttendees = getAllCurAttendees(frmSession.sessionID.data)
            attend4R = ("DMBC 4R Attendees -   " + frmSession.sessionDate.data + "  "
                        + dict(frmSession.sessionType.choices).get(int(frmSession.sessionType.data))
                        )
            if curAttendees and len(curAttendees) > 0:
                tblLabel = f"Attendees - {len(curAttendees)}"

    return render_template("attendance.html",
                           page_heading=attend4R,
                           curAttendees=curAttendees,
                           frmSession=frmSession,
                           tableHeader=tblLabel,
                           foundClients=records)
