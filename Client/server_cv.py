import inspect
import json
import logging
import os
import re
import secrets
import threading as th
import time

import cv2
import numpy as np
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
from PyCameraList.camera_device import list_video_devices
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

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1
        message = record.getMessage()
        # remove timestamp like [19/Sep/2023 14:08:16]
        message = re.sub(r"\[\d+/\w+/\d{4} \d{2}:\d{2}:\d{2}\] ", "", message)
        # remove terminal color code
        message = re.sub(r"\x1b\[\d+m", "", message)
        message = re.sub(r"\x1b\[\d+;\d+m", "", message)
        logger.opt(depth=depth, exception=record.exc_info).log(level, message)


logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

kvm_default_config = {
    "web_title": "KVM Web Control Interface",
    "video": {
        "width": 1280,
        "height": 720,
        "fps": 60,
        "quality": 60,
    },
}


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


class fps_counter:
    def __init__(self, max_sample=40) -> None:
        self.t = time.perf_counter()
        self.max_sample = max_sample
        self.t_list = []
        self.time_list = []

    def update(self) -> None:
        t = time.perf_counter()
        self.t_list.append(t - self.t)
        self.time_list.append(t)
        self.t = t
        if len(self.t_list) > self.max_sample:
            self.t_list.pop(0)
            self.time_list.pop(0)

    def get(self) -> float:
        now = time.perf_counter()
        if len(self.t_list) > 0:
            while len(self.time_list) > 0 and now - self.time_list[0] > 1:
                self.t_list.pop(0)
                self.time_list.pop(0)
            length = len(self.t_list)
            sum_t = sum(self.t_list)
            if sum_t == 0:
                return 0.0
            else:
                return length / sum_t
        return 0.0

    def reset(self):
        self.t_list = []
        self.t = time.perf_counter()


fpc = fps_counter()


class KVM_Server(object):
    def __init__(self, config=kvm_default_config) -> None:
        self.config = config
        self.running = False
        self.camera_opened = False
        self.command_callback = None
        self.auth_required = False

        app.route("/")(self.http_index)
        app.route("/<path:path>")(self.public_file)
        sock.route("/websocket")(self.websocket)
        app.route("/stream")(self.http_stream)
        app.route("/snapshot")(self.http_snapshot)
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

    def open_camera(self, device_name):
        if self.camera_opened:
            return True, ""
        devices = list_video_devices()
        logger.info(f"Found video devices: {devices}")
        if len(devices) == 0:
            return False, "No video device found"
        for id, name in devices:
            if name == device_name:
                video_device = id
                break
        else:
            return False, f"Cannot find video device: {device_name}"
        self.config["video"]["device"] = device_name
        self.cap = cv2.VideoCapture(video_device)
        if not self.cap.isOpened():
            return False, f"Cannot open cv2 camera: {video_device}"
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config["video"]["width"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config["video"]["height"])
        self.cap.set(cv2.CAP_PROP_FPS, self.config["video"]["fps"])
        true_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        true_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        true_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        logger.info(f"Opend camera-{video_device}: {true_width}x{true_height}@{true_fps}fps")
        self.config["video"]["width"] = true_width
        self.config["video"]["height"] = true_height
        self.config["video"]["fps"] = true_fps
        self.image = np.zeros((true_height, true_width, 3), np.uint8)
        self.image_event = th.Event()
        self.camera_opened = True
        return True, ""

    def close_camera(self):
        self.cap.release()
        self.camera_opened = False

    def stream_worker(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            cv2.putText(frame, f"{fpc.get():.6f}fps", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            self.image = frame
            self.image_event.set()

    def get_stream(self):
        while self.running:
            self.image_event.wait()
            self.image_event.clear()
            frame = self.image.copy()
            if self.config["video"]["quality"] == 100:
                data = cv2.imencode(".png", frame)[1]
                yield (b"Content-Type: data/png\r\n\r\n" + data.tobytes() + b"\r\n\r\n--frame\r\n")
            else:
                data = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.config["video"]["quality"]])[1]
                yield (b"Content-Type: data/jpeg\r\n\r\n" + data.tobytes() + b"\r\n\r\n--frame\r\n")
            fpc.update()

    def get_snapshot(self):
        self.image_event.wait()
        self.image_event.clear()
        frame = self.image.copy()
        data = cv2.imencode(".png", frame)[1]
        return data.tobytes()

    def http_stream(self):
        if self.auth_required:
            if not check_auth_secret():
                return redirect(url_for("login", r="http_stream"))
        return Response(self.get_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

    def http_snapshot(self):
        if self.auth_required:
            if not check_auth_secret():
                return redirect(url_for("login", r="http_snapshot"))
        return Response(self.get_snapshot(), mimetype="image/png")

    def http_config(self):
        if self.auth_required:
            if not check_auth_secret():
                return redirect(url_for("login", r="http_config", **request.args))
        res = request.args.get("res", None)
        fps = request.args.get("fps", None)
        quality = request.args.get("quality", None)
        if not any([res, fps, quality]):
            return jsonify(self.config)
        if res is not None:
            video_width = int(res.split("x")[0])
            video_height = int(res.split("x")[1])
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, video_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, video_height)
        if fps is not None:
            video_fps = int(fps)
            self.cap.set(cv2.CAP_PROP_FPS, video_fps)
        true_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        true_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        true_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        self.config["video"]["width"] = true_width
        self.config["video"]["height"] = true_height
        self.config["video"]["fps"] = true_fps
        if quality is not None:
            video_quality = int(quality)
            video_quality = max(0, min(100, video_quality))
            self.config["video"]["quality"] = video_quality
        logger.info(
            f'New config set: {self.config["video"]["width"]}x{self.config["video"]["height"]}@{self.config["video"]["fps"]}fps, quality={self.config["video"]["quality"]}'
        )
        return jsonify(self.config)

    def start_server(self, host, port, device):
        """
        Start the server non-blocking
        """
        assert not self.running, "Server already running"
        if not self.camera_opened:
            ret, msg = self.open_camera(device)
            if not ret:
                raise Exception(msg)
        self.running = True
        self.stream_thread = th.Thread(target=self.stream_worker, daemon=True)
        self.stream_thread.start()
        self.server = make_server(host, port, app, threaded=True, processes=1)
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
        self.stream_thread.join()
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
