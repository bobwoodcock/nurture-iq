from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import json
from sqlalchemy import func, text
from datetime import datetime

with open("config.json") as config_file:
    config = json.load(config_file)

app = Flask(__name__)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = config.get("sqlalchemy_uri")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class BabyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.DateTime, nullable=False)
    activity = db.Column(db.String(512), nullable=False)
    quantity = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.String(512), nullable=True) 
    duration = db.Column(db.Integer, nullable=True)

def __repr__(self):
    hours = self.duration // 60 if self.duration else 0
    minutes = self.duration % 60 if self.duration else 0
    duration_str = f"{hours}h {minutes}m" if self.duration else "N/A"
    comment_str = f", Comment: '{self.comment}'" if self.comment else ""
    return f"<BabyLog {self.activity} at {self.ts}, Quantity: {self.quantity}{duration_str}{comment_str}>"

# Home route
@app.route('/')
def home():
    return render_template('home.html')

# Route to add entries
@app.route('/add', methods=['GET', 'POST'])
def add_entry():
    if request.method == 'POST':
        activities = request.form.getlist('activities')
        ts = request.form['ts']
        comment = request.form['comment']

        # Convert timestamp
        try:
            ts = datetime.strptime(ts, "%Y-%m-%dT%H:%M")
        except ValueError:
            return "Invalid timestamp format", 400

        # Handle quantity
        quantity = request.form.get('quantity', '1')
        try:
            quantity = int(quantity)
        except ValueError:
            quantity = 1

        # Handle duration
        duration = request.form.get('duration', '0')
        try:
            duration = int(duration)
        except ValueError:
            duration = 0

        for activity in activities:
            entry_quantity = quantity if activity in ('Pumped', 'Formula', 'Boob') else 1
            entry_duration = duration if activity in ('Pumped', 'Formula', 'Boob', 'Tummy Time') else None
            new_entry = BabyLog(
                ts=ts,
                activity=activity,
                quantity=entry_quantity,
                comment=comment,
                duration=entry_duration
            )
            db.session.add(new_entry)

        db.session.commit()
        return redirect(url_for('view_entries'))

    return render_template('add_entry.html')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

# Route to view all entries
@app.route('/entries')
def view_entries():
    # Get the current page number from the query string (default is 1)
    page = request.args.get('page', 1, type=int)

    # Get filter inputs from query parameters
    selected_activities = request.args.getlist('activity')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Start building the query
    query = BabyLog.query

    # Apply activity filter if selected
    if selected_activities:
        query = query.filter(BabyLog.activity.in_(selected_activities))

    # Apply date range filter if specified
    if start_date:
        query = query.filter(BabyLog.ts >= start_date)
    if end_date:
        query = query.filter(BabyLog.ts <= end_date)

    # Paginate results
    pagination = query.order_by(BabyLog.ts.desc()).paginate(page=page, per_page=20)

    # Get unique activities for the filter checkboxes
    activities = db.session.query(BabyLog.activity).distinct().order_by(BabyLog.activity).all()
    activities = [activity[0] for activity in activities]

    # Pass the pagination and filter information to the template
    return render_template(
        'view_entries.html',
        pagination=pagination,
        activities=activities,
        selected_activities=selected_activities
    )

@app.route('/delete/<int:entry_id>', methods=['POST'])
def delete_entry(entry_id):
    # Find the entry by id
    entry = BabyLog.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('view_entries'))

@app.route('/analytics/day_aggregated')
def aggregated_view():
    # Get unique activities for checkboxes
    activities = db.session.query(BabyLog.activity).distinct().order_by(BabyLog.activity).all()
    activities = [activity[0] for activity in activities]

    # Get selected activities from query parameters, default to 'Pumped' and 'Formula'
    selected_activities = request.args.getlist('activity') or ['Pumped', 'Formula', 'Boob']

    # Query to aggregate quantities by day and activity, with optional filtering
    query = db.session.query(
        func.date(BabyLog.ts).label('day'),
        BabyLog.activity,
        func.sum(func.coalesce(BabyLog.quantity, 1)).label('total_quantity')
    ).group_by(func.date(BabyLog.ts), BabyLog.activity).order_by(func.date(BabyLog.ts).desc())

    if selected_activities:
        query = query.filter(BabyLog.activity.in_(selected_activities))

    aggregated_data = query.all()

    # Render the data in a template
    return render_template(
        'analytics/day_aggregated.html',
        aggregated_data=aggregated_data,
        activities=activities,
        selected_activities=selected_activities
    )

@app.route('/analytics/daily_feed_quantity_chart')
def daily_feed_quantity_chart():
    return render_template('analytics/daily_feed_quantity.html')

@app.route('/data/daily_feed_quantity')
def daily_feed_quantity():
    result = db.session.execute(text('''
        WITH daily_activities AS (
        SELECT
            DATE(ts) AS day,
            activity,
            CASE
                WHEN activity IN ('Pumped', 'Formula') THEN quantity
                WHEN activity = 'Boob' THEN quantity * 45
                ELSE 0
                END AS feed_quantity
            FROM baby_log
            WHERE activity IN ('Pumped','Formula', 'Boob')
            AND ts BETWEEN NOW() - INTERVAL '1 month' AND NOW()
        )
        SELECT
            day,
            SUM(feed_quantity) as total_quantity
        FROM daily_activities
        GROUP BY day
        ORDER BY day
    '''))

    data = [{'day': str(row[0]), 'total_quantity': row[1]} for row in result]
    return {'data': data}

@app.route('/data/weekly_feed_duration')
def weekly_feed_duration():
    result = db.session.execute(text('''
        WITH boob_qty AS (SELECT
            EXTRACT(YEAR FROM ts) AS ts_year,
            EXTRACT(WEEK FROM ts) AS ts_week,
            CASE WHEN activity IN ('Pumped', 'Formula')
                THEN 'Bottle'
            ELSE activity
            END AS activity,
            CASE WHEN activity = 'Boob'
                THEN quantity * 45
                ELSE quantity
                END AS quantity,
            duration,
            CASE WHEN activity = 'Boob'
                THEN (quantity * 45) / duration
                ELSE quantity / duration
                END AS minutes_per_ml,
            1 AS duration_recorded
        FROM baby_log
        WHERE 
            duration IS NOT NULL
            AND duration > 0
            AND activity in ('Pumped', 'Formula')
            )

        SELECT ts_year AS year,
            ts_week AS week,
            activity,
            AVG(minutes_per_ml) AS avg_mins_per_ml,
            MIN(minutes_per_ml) AS min_minutes_per_ml,
            MAX(minutes_per_ml) AS max_mins_per_ml
        FROM boob_qty
        GROUP BY ts_year, ts_week, activity
        ORDER BY ts_year, ts_week
        ;
    '''))

    data = [{
        'year': str(row[0]),
        'week': str(row[1]),
        'activity': str(row[2]),
        'avg_mins_per_ml': row[3],
        'min_mins_per_ml': row[4],
        'max_mins_per_ml': row[5]
        } for row in result]
    return {'data': data}

@app.route('/analytics/weekly_feed_duration_chart')
def feed_duration_chart():
    return render_template('analytics/weekly_feed_duration.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
