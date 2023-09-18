import json
import logging
import os
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
from flask_sock import Sock
from PyCameraList.camera_device import list_video_devices
from werkzeug.serving import make_server

path = os.path.dirname(os.path.abspath(__file__))

kvm_default_config = {
    "web_title": "KVM Web Control Interface",
    "port": 5000,
    "video": {
        "width": 1280,
        "height": 720,
        "fps": 60,
        "quality": 80,
        "device": "USB Video",
    },
}

app = Flask(__name__)
sock = Sock(app)
app.template_folder = os.path.join(path, "web")
CORS(app, supports_credentials=True, allow_headers="*")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/<path:path>")
def public_file(path):
    return send_from_directory("web", path)


class KVM_Server(object):
    instance = None
    inited = False

    def __new__(cls, *args, **kwargs):
        if KVM_Server.instance is None:
            KVM_Server.instance = object.__new__(cls)
        return KVM_Server.instance

    def __init__(self, config=kvm_default_config) -> None:
        if KVM_Server.inited:
            return
        self.config = config
        self.running = False
        self.log_disabled = False
        self.camera_opened = False
        self.command_callback = None
        app.route("/api/config")(self.get_config)
        sock.route("/websocket")(self.websocket)
        app.route("/stream")(self.http_stream)
        app.route("/snapshot")(self.http_snapshot)
        app.route("/info")(self.http_info)
        app.route("/config")(self.http_config)

    def log(self, msg):
        if not self.log_disabled:
            print(msg)

    def get_config(self):
        self.log(f"get_config: {self.config}")
        return jsonify(self.config)

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
                        self.log(f"Command: {data_type} {data_payload}")
                except Exception as e:
                    self.log(f"Error Command: {e}")

    def register_command_callback(self, callback):
        self.command_callback = callback

    def disable_log(self):
        log = logging.getLogger("werkzeug")
        log.disabled = True
        log.setLevel(logging.ERROR)
        self.log_disabled = True

    def open_camera(self):
        device_name = self.config["video"]["device"]
        devices = list_video_devices()
        self.log(f"Found video devices: {devices}")
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
        self.log(f"Opend camera-{video_device}: {true_width}x{true_height}@{true_fps}fps")
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
            timestr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            cv2.putText(frame, timestr, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            self.image = frame
            self.image_event.set()

    def get_stream(self):
        while self.running:
            self.image_event.wait()
            self.image_event.clear()
            frame = self.image.copy()
            data = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.config["video"]["quality"]])[1]
            yield (b"Content-Type: data/jpeg\r\n\r\n" + data.tobytes() + b"\r\n\r\n--frame\r\n")

    def get_snapshot(self):
        self.image_event.wait()
        self.image_event.clear()
        frame = self.image.copy()
        data = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.config["video"]["quality"]])[1]
        return data.tobytes()

    def http_stream(self):
        return Response(self.get_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

    def http_snapshot(self):
        return Response(self.get_snapshot(), mimetype="image/jpeg")

    def http_info(self):
        return Response(
            f'Device-{self.config["video"]["device"]}: {self.config["video"]["width"]}x{self.config["video"]["height"]}@{self.config["video"]["fps"]}fps',
            mimetype="text/plain",
            status=200,
        )

    def http_config(self):
        res = request.args.get("res", None)
        fps = request.args.get("fps", None)
        quality = request.args.get("quality", None)
        if not any([res, fps, quality]):
            return Response("No config provided, available: res, fps, quality", status=400)
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
        text = f'New config: {self.config["video"]["width"]}x{self.config["video"]["height"]}@{self.config["video"]["fps"]}fps, quality={self.config["video"]["quality"]}'
        self.log(text)
        return Response(text, status=200)

    def _run(self):
        self.server.serve_forever()

    def start_server(self):
        """
        Start the server non-blocking
        """
        assert not self.running, "Server already running"
        if not self.camera_opened:
            ret, msg = self.open_camera()
            if not ret:
                raise Exception(msg)
        self.running = True
        self.stream_thread = th.Thread(target=self.stream_worker, daemon=True)
        self.stream_thread.start()
        self.server = make_server("0.0.0.0", self.config["port"], app, threaded=True, processes=1)
        self.server_thread = th.Thread(target=self._run, daemon=True)
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
    server.disable_log()
    server.start_server()
    while True:
        try:
            time.sleep(1)
            print("Server running")
        except KeyboardInterrupt:
            break
    server.stop_server()
    print("Server stopped")
