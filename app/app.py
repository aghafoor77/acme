import json
import logging
import os
import re
import uuid

from dotenv import load_dotenv
from FileDownloader import FileDownloader

# from config import DB_CONFIG
# from extensions import db
# from create_db import create_database_if_not_exists
from flask import Flask, g, jsonify, request, send_file
from flask_cors import CORS
from JSONHandler import JSONHandler
from RequestFormatter import RequestFormatter
from tasks import process_data_task
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)


@app.before_request
def before_request():
    g.request_token = uuid.uuid4().hex[:10]  # 10-char token
    print(g.request_token)


formatter = RequestFormatter(
    fmt="[%(asctime)s] [%(filename)s:%(lineno)d] [%(levelname)s] [token=%(request_token)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# === 1. Console Handler (Terminal Output) ===
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# === 2. File Handler ===
log_file_path = "../logs/"  # Make sure the 'logs' folder exists
os.makedirs(log_file_path, exist_ok=True)
log_file_path = f"{log_file_path}/acme.log"  # Make sure the 'logs' folder exists
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
logger = logging.getLogger(__name__)

# Step 1: Ensure DB exists
# create_database_if_not_exists()
# logger.info(f"Successfully created database '{DB_CONFIG['database']}'!")

# app.config['SQLALCHEMY_DATABASE_URI'] = (
#        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
#        )
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db.init_app(app)
# with app.app_context():
#    db.create_all()
#    logger.info("Successfully created persistant schema !")


# Security & config
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024  # 10 KB max file size
ALLOWED_EXTENSIONS = {"yaml", "yml", "json"}

# Email regex (basic)
EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


load_dotenv()
ACME_DATA_DIR = os.getenv("ACME_DATA_DIR")


@app.route("/pm/<uuid_value>", methods=["GET"])
def get_pm(uuid_value):
    print(ACME_DATA_DIR)

    fileDownloader = FileDownloader(ACME_DATA_DIR)
    file_path = fileDownloader.get_file_from_uuid(uuid_value, "pm")
    if isinstance(file_path, str):
        return send_file(file_path, as_attachment=True)
    else:
        return file_path


@app.route("/ev/<uuid_value>", methods=["GET"])
def get_ev(uuid_value):
    fileDownloader = FileDownloader(ACME_DATA_DIR)
    file_path = fileDownloader.get_file_from_uuid(uuid_value, "ev")
    if isinstance(file_path, str):
        return send_file(file_path, as_attachment=True)
    else:
        return file_path


@app.route("/upload", methods=["POST"])
def upload():
    logger.info("Request received !")
    # Ensure JSON part exists
    if not request.form.get("email") or not request.form.get("vdata"):
        logger.error("Invalid data received !")
        return jsonify({"error": "Missing 'email' or 'vdata' in form data"}), 400

    email = request.form.get("email")
    vdata = request.form.get("vdata")
    if vdata == "":
        return jsonify({"error": "Missing 'vdata' in form data !"}), 400

    logger.info("Data extracted from request !")
    # Validate email
    if not EMAIL_REGEX.match(email):
        logger.error(f"Invalid email address '{email}' !")
        return jsonify({"error": "Invalid email address"}), 400

    # Validate file
    file = request.files.get("file")
    if file is None or file.filename == "":
        logger.error("Invalid file or file is missing !")
        return jsonify({"error": "No file uploaded"}), 400

    if not allowed_file(file.filename):
        logger.error("Invalid file format '{file.filename}' !")
        return (
            jsonify({"error": "Unsupported file type. Only YAML or JSON allowed."}),
            400,
        )

    # Secure filename (prevent directory traversal)
    filename = secure_filename(file.filename)

    # Read and process file content in memory
    file_content = file.read().decode("utf-8")

    # Double check size (even though Flask limits it)
    # content_size = len(file_content)
    if len(file_content) > app.config["MAX_CONTENT_LENGTH"]:
        logger.error(
            "Invalid file size, it should be less than 10 K  'Size = {content_size}' !"
        )
        return jsonify({"error": "File size exceeds 10KB limit"}), 400

    logger.info("Processing request for vulernability test cases generation !")
    # TODO: Process the data (e.g., save to DB, validate vdata, parse file content)

    uuid_value = str(uuid.uuid4())

    output_dir = f"{ACME_DATA_DIR}{uuid_value}/"
    os.makedirs(output_dir, exist_ok=True)
    jsonNHandler = JSONHandler()
    opeanapi = f"{output_dir}req_{filename}"
    jsonNHandler.save_string(f"{opeanapi}", file_content)

    process_data_task.delay(email, uuid_value, opeanapi, output_dir, json.loads(vdata))

    # new_upload = Upload(
    #   id=uuid_value, email=email, status=False, vdata=vdata, filename=opeanapi
    # )
    # db.session.add(new_upload)
    # db.session.commit()
    return (
        jsonify(
            {
                "message": "ACME has received your request and it will be processed shortly. Please check your email to download the generated test cases and environment variables.",
                "email": email,
            }
        ),
        200,
    )


# Optional: Custom error handler for large files
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File is too large. Max allowed is 10KB."}), 413


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
