from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import humanize

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


@app.route("/")
def index():
    tasks = Task.query.all()
    # finished_sessions = Session.query.filter(
    #     Session.start_time.isnot(None), Session.end_time.isnot(None)
    # ).all()

    return render_template(
        "index.html",
        tasks=tasks,
        format_time=format_time,
        format_relative_time=format_relative_time,
        group_sessions_by_date=group_sessions_by_date,
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


def format_time(seconds):
    return str(timedelta(seconds=seconds))


def format_relative_time(start_time, end_time):
    if end_time:
        return humanize.naturaldelta(end_time - start_time)
    else:
        return "Ongoing"


def group_sessions_by_date(sessions):
    grouped_sessions = {}
    for session in sessions:
        session_date = session.start_time.date()
        grouped_sessions.setdefault(session_date, []).append(session)
    return grouped_sessions


# Use app context to create tables
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
