from flask import render_template, Blueprint, request, flash
from flask_wtf import FlaskForm
from utils.dbDeb import getAllFriends
from wtforms import BooleanField, SubmitField

bpShowAllFriends = Blueprint('ShowAllFriends_blueprint', __name__)


class showRegistrantsForm(FlaskForm):
    InlcudeUnpaid = BooleanField('Inlucde Unpaid Registrants')
    OnlyUnpaid = BooleanField('ONLY Unpaid Registrants')
    show = SubmitField("Go")


# ----------  show all registrants ------------------------
@bpShowAllFriends.route('/ShowAllFriends', methods=["POST", "GET"])
def viewAll():
    form = showRegistrantsForm(request.form)
    seeAll = "Select view"
    if request.method == "POST":
        try:
            getType = 0     # by default only paid registrants this year,
            onlyUnpaid = form.OnlyUnpaid.data
            if onlyUnpaid:  # user wants to see unpaid only
                getType = 1
                seeAll = "All unpaid registrants on database"
            else:
                incUpaid = form.InlcudeUnpaid.data
                if incUpaid:
                    getType = 2  # all paid and unpaid
                    seeAll = "All registrants on database"
                else:
                    seeAll = "Paid registrants this year"

            allRegistrants = getAllFriends(getType)
        except Exception as error:
            flash(str(error))

        return render_template("allRegistrants.html",
                               page_heading=seeAll,
                               form=form,
                               registrants=allRegistrants)
    else:
        return render_template("allRegistrants.html",
                               page_heading=seeAll,
                               form=form,
                               registrants=None)
