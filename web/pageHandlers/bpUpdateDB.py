from flask import Blueprint, request, render_template, flash, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, HiddenField, BooleanField
from wtforms.validators import DataRequired, Length
from utils.dbDeb import addClient, deleteClient, getListOfActivity, UpdateClient, getClientByID, findFamilyID
# ================================= implements add/update client records =======================

bpUpdateDB = Blueprint('WorkInDB_blueprint', __name__)


# --------------- Create form definition ---------------
class updateClientForm(FlaskForm):
    id = HiddenField("id")
    firstName = StringField(label="First Name",
                            validators=[DataRequired("First Name is required"),
                                        Length(min=1, max=15,
                                               message="First name must be between 3 to 15 characters")])

    lastName = StringField(label="Last Name",
                           validators=[DataRequired("Last Name is required"),
                                       Length(min=2, max=15)])

    phoneNumber = StringField(label="Phone number", id="phone",
                              validators=[DataRequired("Phone number is required"),
                                          Length(min=10, max=15,
                                                 message="Phone number must be 10 to 15 characters")])

    address = StringField(label="address")
    ECName = StringField(label="Emergency Contact",
                         validators=[Length(min=0, max=30,
                                            message="First name must be between 3 to 15 characters")])

    ECPhone = StringField(label="Emergency contact Phone", id="ecPhone",
                          validators=[Length(min=10, max=15,
                                             message="Phone number must be 10 to 15 characters")])

    Email = StringField(label="Email", validators=[Length(min=0, max=50)])
    FamilyID = HiddenField()
    FamilyName = StringField(label="FamilyOf",
                             validators=[Length(min=0, max=50)],
                             render_kw={"placeholder": "firstName lastName"})
    IsPrimary = BooleanField("Primary Family member")
    FeesPaid = StringField(label="Fees paid", validators=[Length(min=0, max=50)])
    # ======== get activiity list from database
    MainActivity = SelectField("Favourite Activity")
    dateRegistered = StringField(label="Register date",
                                 validators=[Length(min=0, max=10)],
                                 render_kw={"placeholder": "yyyy-mm-dd"})
    Remarks = StringField(label="Remarks")
    submit = SubmitField('Update Client Record')


# -------------- add or update single record in db, form parameter id can be absent --------------
@bpUpdateDB.route("/updateRecord", methods=["POST", "GET"])
def updateRecord():
    id = request.args.get('id', 0)
    todo = request.args.get('todo', None)

    if request.method == "GET":
        form = None
        if id:
            client = getClientByID(id)
            form = updateClientForm(data=client)
            if form.id.data == form.FamilyID.data:  # if this is the primary family member
                form.IsPrimary.data = True
        else:
            form = updateClientForm()
        actChoices = getListOfActivity()
        if actChoices is not None:
            form.MainActivity.choices = [(sel["actid"], sel["actname"]) for sel in actChoices]
        if not form.id.data:
            addHeading = "New Registration"
            form.submit.label.text = "Submit"
        else:
            if todo == 'update':
                addHeading = "Update Record"
                form.submit.label.text = "Update"
            elif todo == 'delete':
                addHeading = "Please make sure this is the Record to DELETE"
                form.submit.label.text = "DELETE"

# ========= if all is well, insert, update of delete the database record ============
    if request.method == "POST":

        form = updateClientForm()
        try:

            if not form.id.data:    # if id not assigned yet, it is a new client
                # ----------- try to get the family id of the family name entered --------
                if form.IsPrimary.data:   # if this is primary family member, add it
                    form.FamilyID.data = '0'    # indicate it
                elif form.FamilyName.data:      # if family name is entered try to find it
                    form.FamilyID.data = findFamilyID(form.FamilyName.data.replace("'", "''").strip())
            #  ------------------ add or update client data,-------------------------------
            #  note that in firstName, lastName, address, ECName, and Remarks may have
            #  single quote, which would cause problems when putting in database, so
            #  we need to escape them by doubling them
                retcode = addClient(form.firstName.data.replace("'", "''").strip(),
                                    form.lastName.data.replace("'", "''").strip(),
                                    form.phoneNumber.data,
                                    form.address.data.replace("'", "''").strip(),
                                    form.ECName.data.replace("'", "''").strip(),
                                    form.ECPhone.data,
                                    form.Email.data,
                                    form.FeesPaid.data,
                                    form.FamilyID.data,
                                    form.MainActivity.data,
                                    form.dateRegistered.data.replace("'", "''").strip(),
                                    form.Remarks.data.replace("'", "''").strip())
                if retcode == -1:
                    raise Exception("Client already exists, please search it and update client info")
                else:
                    retMsg = "New attendee added successfully"
            else:
                if todo == 'update':
                    if not form.FamilyID.data:          # if current familyid is nothing
                        if form.IsPrimary.data:         # if this is primary family member, add it
                            form.FamilyID.data = '0'    # indicate it
                        elif form.FamilyName.data:      # if family name is entered try to find it
                            form.FamilyID.data = findFamilyID(form.FamilyName.data.replace("'", "''").strip())

                    UpdateClient(form.id.data,
                                 form.firstName.data.replace("'", "''").strip(),
                                 form.lastName.data.replace("'", "''").strip(),
                                 form.phoneNumber.data,
                                 form.address.data.replace("'", "''").strip(),
                                 form.ECName.data.replace("'", "''").strip(),
                                 form.ECPhone.data,
                                 form.Email.data,
                                 form.FeesPaid.data,
                                 form.FamilyID.data,
                                 form.MainActivity.data,
                                 form.dateRegistered.data.replace("'", "''").strip(),
                                 form.Remarks.data.replace("'", "''").strip())

                    retMsg = "Attendee Information Updated"
                elif todo == 'delete':
                    deleteClient(id)
                    retMsg = "Record deleted"

        except Exception as error:
            flash(str(error))
            return render_template("updateDB.html",
                                   id=id,
                                   page_heading="Database update error",
                                   form=form)

        # ------ if update successful ---------------------
        return render_template("updateDBDone.html",
                               page_heading=retMsg,
                               first_name=form.firstName.data,
                               last_name=form.lastName.data,
                               phone_number=form.phoneNumber.data)

    return render_template("updateDB.html", page_heading=addHeading, form=form)
