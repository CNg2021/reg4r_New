from flask import Blueprint, render_template

bpIndex = Blueprint('Index_blueprint', __name__)


# ---------- launch it as background ------------
@bpIndex.route("/index", methods=['GET', 'POST'])
def index():
    return render_template("index.html", page_heading="DMBC 4R")
