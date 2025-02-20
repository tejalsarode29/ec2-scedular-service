from flask import Flask, request, jsonify
from flask_apscheduler.scheduler import APScheduler
import sqlite3
import json
import datetime
import logging
from logging.handlers import RotatingFileHandler
import os

app = Flask(__name__)
scheduler = APScheduler()

LOG_FOLDER = "logs"
os.makedirs(LOG_FOLDER, exist_ok=True)

log_file = os.path.join(LOG_FOLDER, 'scheduler.log')
handler = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=5)
logging.basicConfig(handlers=[handler], level=logging.INFO, 
                    format='%(asctime)s %(levelname)s:%(message)s')

DB_FILE = "scheduler.db"

def init_db():
    """Initialize the SQLite database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                function_name TEXT NOT NULL,
                parameters TEXT NOT NULL,
                cron_expression TEXT NOT NULL,
                status INTEGER DEFAULT 1
            )
        """)
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.error(f"Error initializing database: {e}")

def get_scheduled_jobs():
    """Retrieve active jobs from the database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, function_name, parameters, cron_expression FROM jobs WHERE status=1")
        jobs = cursor.fetchall()
        conn.close()
        return jobs
    except Exception as e:
        logging.error(f"Error retrieving scheduled jobs: {e}")
        return []

# Function Mappings
def sample_function(name, age):
    logging.info(f"Executing sample_function at {datetime.datetime.now()} with name={name}, age={age}")

FUNCTION_MAP = {
    "sample_function": sample_function
}

def execute_function(func_name, params):
    """Dynamically execute a function with parameters"""
    try:
        if func_name in FUNCTION_MAP:
            FUNCTION_MAP[func_name](**params)
        else:
            logging.warning(f"Function {func_name} not found!")
    except Exception as e:
        logging.error(f"Error executing function {func_name}: {e}")

# Schedule Jobs from Database
def schedule_jobs():
    try:
        jobs = get_scheduled_jobs()
        existing_jobs = {job.id for job in scheduler.get_jobs()}
        
        for job in jobs:
            job_id, func_name, params, cron_expr = job
            if str(job_id) in existing_jobs:
                continue  # Skip if job is already scheduled
            
            params = json.loads(params)  # Convert JSON string to dict
            cron_parts = cron_expr.split()  # Example: "*/1 * * * *"
            
            scheduler.add_job(
                func=execute_function, 
                trigger="cron", 
                args=[func_name, params],
                id=str(job_id), 
                minute=cron_parts[0], hour=cron_parts[1], 
                day=cron_parts[2], month=cron_parts[3], 
                day_of_week=cron_parts[4]
            )
            logging.info(f"Scheduled Job {job_id}: {func_name} with {params}")
    except Exception as e:
        logging.error(f"Error scheduling jobs: {e}")

# Flask Routes
@app.route("/add_job", methods=["POST"])
def add_job():
    """API to add a job"""
    try:
        data = request.json
        function_name = data.get("function_name")
        parameters = json.dumps(data.get("parameters", {}))
        cron_expression = data.get("cron_expression")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO jobs (function_name, parameters, cron_expression) VALUES (?, ?, ?)",
                       (function_name, parameters, cron_expression))
        conn.commit()
        conn.close()
        
        schedule_jobs()  # Reschedule jobs
        logging.info(f"Job added successfully: {function_name} with {parameters} and cron {cron_expression}")
        return jsonify({"message": "Job added successfully"}), 201
    except Exception as e:
        logging.error(f"Error adding job: {e}")
        return jsonify({"message": "Error adding job"}), 500

@app.route("/list_jobs", methods=["GET"])
def list_jobs():
    """API to list jobs"""
    try:
        jobs = get_scheduled_jobs()
        return jsonify(jobs)
    except Exception as e:
        logging.error(f"Error listing jobs: {e}")
        return jsonify({"message": "Error listing jobs"}), 500

@app.route("/delete_job/<int:job_id>", methods=["DELETE"])
def delete_job(job_id):
    """API to delete a job"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        conn.commit()
        conn.close()
        
        scheduler.remove_job(str(job_id))  # Remove from APScheduler
        logging.info(f"Job deleted successfully: {job_id}")
        return jsonify({"message": "Job deleted successfully"}), 200
    except Exception as e:
        logging.error(f"Error deleting job: {e}")
        return jsonify({"message": "Error deleting job"}), 500

# Run Flask and APScheduler
if __name__ == "__main__":
    try:
        init_db()
        schedule_jobs()
        scheduler.init_app(app)
        scheduler.start()
        logging.info("Scheduler started successfully.")
        app.run(debug=True)
    except Exception as e:
        logging.error(f"Error starting application: {e}")
