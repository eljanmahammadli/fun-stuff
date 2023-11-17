from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tasks.db"
db = SQLAlchemy(app)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sessions = db.relationship("Session", backref="task", lazy=True)


class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    spent_time = db.Column(db.Interval)


@app.route("/")
def index():
    tasks = Task.query.all()
    today = datetime.utcnow().date()

    # Calculate total spent time for each task today
    today_totals = {}
    for task in tasks:
        task_sessions_today = Session.query.filter(
            Session.task_id == task.id, Session.start_time >= today, Session.end_time.isnot(None)
        ).all()
        total_time = sum(
            (session.end_time - session.start_time for session in task_sessions_today), timedelta()
        )
        today_totals[task.name] = total_time

    # Calculate total spent time for each task overall
    all_time_totals = {}
    for task in tasks:
        all_sessions = (
            Session.query.filter_by(task_id=task.id).filter(Session.end_time.isnot(None)).all()
        )
        total_time_all = sum(
            (session.end_time - session.start_time for session in all_sessions), timedelta()
        )
        all_time_totals[task.name] = total_time_all

    return render_template(
        "index.html",
        tasks=tasks,
        format_time=format_time,
        group_sessions_by_date=group_sessions_by_date,
        today_totals=today_totals,
        all_time_totals=all_time_totals,
    )


@app.route("/add_task", methods=["POST"])
def add_task():
    task_name = request.form["task_name"]
    new_task = Task(name=task_name)
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/start_session", methods=["POST"])
def start_session():
    task_id = request.form["task_id"]
    task = Task.query.get(task_id)

    if task:
        new_session = Session(task=task)
        db.session.add(new_session)
        db.session.commit()

    return redirect(url_for("index"))


@app.route("/end_session/<int:session_id>")
def end_session(session_id):
    session = Session.query.get(session_id)

    if session and not session.end_time:
        session.end_time = datetime.utcnow()
        session.spent_time = session.end_time - session.start_time
        db.session.commit()

    return redirect(url_for("index"))


@app.route("/delete_session/<int:session_id>")
def delete_session(session_id):
    session = Session.query.get(session_id)

    if session:
        if session.end_time:
            # Session is finished, delete it
            db.session.delete(session)
        else:
            # Session is ongoing, mark it as deleted (optional: you can keep the record for reference)
            session.deleted = True

        db.session.commit()

    return redirect(url_for("index"))


def format_time(raw_time):
    # If raw_time is an integer, assume it represents seconds
    if isinstance(raw_time, int):
        timedelta_obj = timedelta(seconds=raw_time)
    elif isinstance(raw_time, timedelta):
        timedelta_obj = raw_time
    else:
        raise ValueError("raw_time must be either an integer or a timedelta object")

    # Extract components (hours, minutes, seconds)
    hours, remainder = divmod(timedelta_obj.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format the time based on components
    if hours > 0:
        return f"{hours} hour {minutes} min"
    elif minutes > 0:
        return f"{minutes} min"
    else:
        return f"{seconds} sec"


def group_sessions_by_date(tasks):
    grouped_sessions = {}
    for task in tasks:
        for session in task.sessions:
            session_date = session.start_time.date()
            if session_date not in grouped_sessions:
                grouped_sessions[session_date] = {}
            if task.name not in grouped_sessions[session_date]:
                grouped_sessions[session_date][task.name] = []
            grouped_sessions[session_date][task.name].append(session)
    return grouped_sessions


# Use app context to create tables
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
