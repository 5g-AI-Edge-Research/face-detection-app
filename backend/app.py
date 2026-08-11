from __future__ import annotations

import os
import time

import cv2
import numpy as np
from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_IMAGE_BYTES", "2500000"))

SITE_NAME = os.getenv("SITE_NAME", "mec-edge")
SIMULATED_DELAY_MS = max(0.0, float(os.getenv("SIMULATED_DELAY_MS", "0")))
PORT = int(os.getenv("PORT", "5002"))

FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def health_payload():
    return {
        "ok": True,
        "status": "ok",
        "service": "face-detection",
        "site": SITE_NAME,
        "simulated_delay_ms": SIMULATED_DELAY_MS,
    }


@app.get("/health")
@app.get("/face/health")
def health():
    return jsonify(health_payload())


@app.post("/detect")
@app.post("/face/detect")
def detect():
    started = time.perf_counter()
    if "image" not in request.files:
        return jsonify(ok=False, error="missing 'image' file field"), 400

    data = request.files["image"].read()
    if not data:
        return jsonify(ok=False, error="empty image"), 400

    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return jsonify(ok=False, error="could not decode image"), 400

    if SIMULATED_DELAY_MS:
        time.sleep(SIMULATED_DELAY_MS / 1000.0)

    inference_started = time.perf_counter()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
    )
    inference_ms = (time.perf_counter() - inference_started) * 1000.0
    total_ms = (time.perf_counter() - started) * 1000.0

    return jsonify(
        ok=True,
        service="face-detection",
        site=SITE_NAME,
        image_width=int(image.shape[1]),
        image_height=int(image.shape[0]),
        image_bytes=len(data),
        face_count=len(faces),
        faces=[
            {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
            for (x, y, w, h) in faces
        ],
        inference_ms=round(inference_ms, 3),
        processing_ms=round(total_ms, 3),
        simulated_delay_ms=SIMULATED_DELAY_MS,
    )


@app.errorhandler(413)
def too_large(_error):
    return jsonify(ok=False, error="image too large"), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
