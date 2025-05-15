from flask import Flask, render_template, request, redirect, url_for, session, Blueprint, jsonify
from datetime import datetime, time
from src.utils.helpers import take_the_seconds
from src.utils.calculator_helpers import *

app = Flask(__name__)
calculator_router = Blueprint('calculator', __name__)

@calculator_router.route("/calculate/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            distance = float(request.form["distance"])
            goal_time = request.form["goal_time"]

            if distance <= 0:
                raise ValueError("Distance must be positive.")
            datetime.strptime(goal_time, "%H:%M:%S")

            total_seconds = calculate_total_seconds(goal_time)
            pace_data = initialize_paces(distance, total_seconds)

            session["pace_data"] = pace_data
            session["distance"] = distance
            session["total_seconds"] = total_seconds

            return redirect(url_for("calculator.pace_adjustment"))
        except Exception as e:
            return render_template("data_calculate.html", error=str(e))
    return render_template("data_calculate.html")



@calculator_router.route("/pace-adjustment")
def pace_adjustment():
    pace_data = session.get("pace_data")
    distance = session.get("distance")

    if not pace_data:
        pace_data = {}
    pace_data_mm_ss = {km: convert_seconds_to_minutes(take_the_seconds(pace)).strftime("%M:%S") for km, pace in pace_data.items()}

    return render_template(
        "pace_adjustment.html", 
        distance=distance, 
        pace_data=pace_data_mm_ss
    )


@calculator_router.route("/update_paces", methods=["POST"])
def update_paces():
    data = request.get_json()
    changed_km = str(data["changed_km"])
    new_pace_seconds = int(data["new_pace"])

    pace_data = session.get("pace_data", {})
    total_seconds = session.get("total_seconds", 0)

    pace_data[changed_km] = convert_seconds_to_minutes(
        new_pace_seconds).strftime("%H:%M:%S")

    pace_data = distribute_the_change(pace_data, changed_km, total_seconds)

    session["pace_data"] = pace_data

    pace_data_seconds = {km: take_the_seconds(
        pace) for km, pace in pace_data.items()}

    return jsonify(pace_data_seconds)
