import inspect
import json
import logging
import os
import re
import secrets
import subprocess
import threading as th
import time

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from flask_sock import Sock
from loguru import logger
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.serving import make_server

PATH = os.path.dirname(os.path.abspath(__file__))


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1
        message = record.getMessage()
        message = re.sub(r"\[\d+/\w+/\d{4} \d{2}:\d{2}:\d{2}\] ", "", message)
        message = re.sub(r"\x1b\[\d+m", "", message)
        message = re.sub(r"\x1b\[\d+;\d+m", "", message)
        logger.opt(depth=depth, exception=record.exc_info).log(level, message)


logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


app = Flask(__name__, static_folder=os.path.join(PATH, "web"), static_url_path="")
sock = Sock(app)
cors = CORS(app, supports_credentials=True, allow_headers="*")
auth = HTTPBasicAuth()

app.template_folder = os.path.join(PATH, "web")

auth_users = {}
auth_secrets = {None: False}


def generate_secret():
    global auth_secrets
    secret = secrets.token_hex(16)
    while secret in auth_secrets:
        secret = secrets.token_hex(16)
    auth_secrets[secret] = False
    return secret


def add_auth_user(username, password):
    global auth_users
    auth_users[username] = generate_password_hash(password)


def count_auth_users():
    global auth_users
    return len(auth_users)


@auth.verify_password
def verify_password(username, password):
    if username in auth_users and check_password_hash(auth_users[username], password):
        return username


def get_browser_uuid():
    data = request.headers.get("User-Agent", "Unknown")
    return hash(data)


@app.route("/login")
@auth.login_required
def login():
    args = request.args.copy()
    red = args.pop("r", None)
    _ = args.pop("s", None)
    if red not in ["http_index", "http_stream", "http_snapshot", "http_info", "http_config"]:
        return Response(f"Invalid redirect: {red}", status=401)
    secret = generate_secret()
    broswer_id = get_browser_uuid()
    logger.info(f"Login: {auth.current_user()} - {secret} - {broswer_id}")
    auth_secrets[secret] = broswer_id
    return redirect(url_for(red, s=secret, **args))


def check_auth_secret():
    secret = request.args.get("s", None)
    if secret is None:
        return False
    if secret not in auth_secrets:
        return False
    if auth_secrets[secret] == get_browser_uuid():
        return True
    auth_secrets.pop(secret)
    logger.info(f"Logout: {secret}")
    return False


class KVM_Server(object):
    def __init__(self) -> None:
        self.running = False
        self.camera_opened = False
        self.command_callback = None
        self.auth_required = False

        app.route("/")(self.http_index)
        app.route("/<path:path>")(self.public_file)
        sock.route("/websocket")(self.websocket)
        app.route("/config")(self.http_config)

    def http_index(self):
        if self.auth_required:
            if not check_auth_secret():
                return redirect(url_for("login", r="http_index"))
        return render_template("index.html")

    def public_file(self, path):
        return send_from_directory("web", path)

    def websocket(self, sock):
        while True:
            data = sock.receive()
            if data:
                try:
                    jdata = json.loads(data)
                    data_type = jdata["type"]
                    data_payload = jdata["payload"]
                    if self.command_callback is not None:
                        self.command_callback(data_type, data_payload)
                    else:
                        logger.debug(f"Command: {data_type} {data_payload}")
                except Exception as e:
                    logger.error(f"Error Command: {e}")

    def register_command_callback(self, callback):
        self.command_callback = callback

    def add_arg(self, lst: list, config: dict, fmt: str, arg_name: str) -> list:
        if arg := config.get(arg_name, None):
            lst.extend([fmt, str(arg)])
        return lst

    def open_camera(self, us_config):
        if self.camera_opened:
            return True, ""
        args = []
        args = self.add_arg(args, us_config, "-s", "host")
        args = self.add_arg(args, us_config, "-p", "video_port")
        args = self.add_arg(args, us_config, "-d", "device")
        args = self.add_arg(args, us_config, "-r", "res")
        args = self.add_arg(args, us_config, "-m", "format")
        args = self.add_arg(args, us_config, "-q", "quality")
        args = self.add_arg(args, us_config, "-w", "workers")
        args = self.add_arg(args, us_config, "-c", "encoder")
        args = self.add_arg(args, us_config, "--user", "user")
        args = self.add_arg(args, us_config, "--passwd", "password")
        args.append("--allow-origin=\\*")
        args.append("-l")
        args.append("--exit-on-parent-death")
        if "extra" in us_config and us_config["extra"]:
            args.extend(us_config["extra"].split(" "))
        logger.debug(f"Stream process args: {args}")
        excutable = "ustreamer"
        self.process = subprocess.Popen([excutable] + args)
        logger.info(f"Stream process started: {self.process.pid}")
        self.camera_opened = True
        return True, ""

    def close_camera(self):
        self.process.kill()
        logger.info("Stream process killed")
        self.process.wait()
        self.camera_opened = False

    def get_config(self):
        config = {
            "web_title": "KVM Web Control Interface",
            "port": self.us_config["video_port"],
            "video": {
                "width": self.us_config["res"].split("x")[0],
                "height": self.us_config["res"].split("x")[1],
                "format": self.us_config["format"],
                "quality": self.us_config["quality"],
            },
        }
        return config

    def reload_camera(self):
        self.close_camera()
        self.open_camera(self.us_config)


    def http_config(self):
        width = request.args.get("width", None)
        height = request.args.get("height", None)
        quality = request.args.get("quality", None)
        format = request.args.get("format", None)
        if len(request.args) == 0:
            return jsonify(self.get_config())
        if all([width, height]):
            self.us_config["res"] = f"{width}x{height}"
        if format is not None:
            self.us_config["format"] = format
        if quality is not None:
            video_quality = int(quality)
            video_quality = max(0, min(100, video_quality))
            self.us_config["quality"] = video_quality
        logger.info(f"New config set: {self.us_config}")
        th.Thread(target=self.reload_camera, daemon=True).start()
        return jsonify(self.get_config())

    def start_server(self, host, port, config: dict, block=False):
        """
        Start the server non-blocking
        """
        assert not self.running, "Server already running"
        self.us_config = config
        if not self.camera_opened:
            ret, msg = self.open_camera(config)
            if not ret:
                raise Exception(msg)
        self.running = True
        self.server = make_server(host, port, app, threaded=True, processes=1)
        self.server.log_startup()
        if block:
            self.server.serve_forever()
        else:
            self.server_thread = th.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()

    def stop_server(self):
        """
        Stop the server
        """
        assert self.running, "Server not running"
        self.running = False
        self.server.shutdown()
        self.server_thread.join()
        self.close_camera()


if __name__ == "__main__":
    server = KVM_Server()
    add_auth_user("admin", "admin")
    server.auth_required = False
    server.start_server("0.0.0.0", 5000, "USB Video")
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            server.stop_server()
            break
