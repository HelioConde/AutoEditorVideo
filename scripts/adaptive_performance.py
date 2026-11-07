"""Locate face motion controls in the original illustration, once per source."""

from pathlib import Path
import hashlib
import math

import numpy as np
from PIL import Image, ImageOps

MODEL = Path(__file__).parent / "models/yunet/face_detection_yunet_2023mar.onnx"


def _eye(rgb, point, face_width):
    """Find the two sclera highlights separated by a dark iris near a landmark."""
    import cv2

    height, width = rgb.shape[:2]
    x, y = point
    left = max(0, int(x - 0.23 * face_width))
    top = max(0, int(y - 0.12 * face_width))
    crop = rgb[
        top : min(height, math.ceil(y + 0.12 * face_width)),
        left : min(width, math.ceil(x + 0.23 * face_width)),
    ]
    if min(crop.shape[:2]) < 5:
        return None
    # Sclerae tend to be brighter and less saturated than surrounding skin.
    patch = cv2.resize(crop, (88, 48), interpolation=cv2.INTER_LINEAR).astype(
        np.float32
    )
    light = patch.mean(axis=2) - 0.7 * (patch.max(axis=2) - patch.min(axis=2))
    light = cv2.GaussianBlur(light, (3, 3), 0.8)
    best = None
    for distance in (11, 15, 19, 23):
        a = light[5:-5, : -2 * distance]
        b = light[5:-5, 2 * distance :]
        middle = light[5:-5, distance:-distance]
        contrast = np.minimum(a, b) - middle
        peak = np.minimum(a, b)
        # Favor landmarks near the prediction, but allow stylized wide-set eyes.
        yy, xx = np.indices(middle.shape)
        score = (
            contrast
            + 0.20 * peak
            - 0.55 * abs(xx + distance - 44)
            - 0.55 * abs(yy + 5 - 24)
        )
        score[(contrast < 35) | (peak < 60)] = -1000
        iy, ix = np.unravel_index(score.argmax(), score.shape)
        if best is None or score[iy, ix] > best[0]:
            best = (score[iy, ix], ix + distance, iy + 5, distance)
    score, cx, cy, radius = best
    if score < 45:
        return None
    # Find the upper lash and lower rim from nearby vertical gradients.
    center_x = int(cx)
    band = light[:, center_x - int(radius) : center_x + int(radius) + 1]
    edges = np.mean(abs(np.gradient(band, axis=0)), axis=1)
    above = max(1, cy - 14)
    below = min(47, cy + 14)
    y0 = above + int(edges[above : cy - 1].argmax())
    y1 = cy + 2 + int(edges[cy + 2 : below + 1].argmax())
    if min(edges[y0], edges[y1]) < 3 or y1 - y0 < 6:
        return None
    sx, sy = crop.shape[1] / 88, crop.shape[0] / 48
    return [
        round(left + cx * sx, 2),
        round(top + (y0 + y1) * 0.5 * sy, 2),
        round(radius * 1.30 * sx, 2),
        round((y1 - y0) * 0.50 * sy, 2),
    ]


def _locate_free_arms(rgba, rgb, faces):
    """Use an isolated person's silhouette to crop the pose estimator's input."""
    import cv2

    alpha = rgba[:, :, 3]
    if alpha.min() > 64:
        return
    _, labels, stats, _ = cv2.connectedComponentsWithStats(
        (alpha > 96).astype(np.uint8)
    )
    net = None
    for face in faces:
        x, y, fw, fh = face["box"]
        center = np.array([x + fw / 2, y + fh / 2])
        component = labels[int(center[1]), int(center[0])]
        if component == 0:
            continue
        left, top, width, height, _ = stats[component]
        if height < 2.8 * fh:
            continue
        side = int(max(width, height) * 1.15)
        origin = np.array([left + (width - side) / 2, top + (height - side) / 2])
        scale = 256 / side
        affine = np.array(
            [[scale, 0, -origin[0] * scale], [0, scale, -origin[1] * scale]]
        )
        crop = cv2.warpAffine(rgb, affine, (256, 256), borderValue=(160, 160, 160))
        if net is None:
            net = cv2.dnn.readNet(
                str(
                    MODEL.parent.parent
                    / "mediapipe-pose/pose_estimation_mediapipe_2023mar.onnx"
                )
            )
        net.setInput(crop.astype(np.float32)[None] / 255)
        landmarks, confidence, *_ = net.forward(net.getUnconnectedOutLayersNames())
        if confidence.item() < 0.85:
            continue
        raw = landmarks.reshape(-1, 5)
        points = raw[:, :2] / scale + origin
        if np.linalg.norm(points[0] - center) > 0.53 * fh:
            continue  # A nearby person was picked up by the pose network.
        best = 0
        for elbow, wrist, finger in ((13, 15, 19), (14, 16, 20)):
            confidence = float(raw[[elbow, wrist, finger], 3:5].min())
            if confidence < max(1.6, best):  # logit 1.6 is ~83% visibility/presence.
                continue
            arm = points[[elbow, wrist, finger]]
            length = np.linalg.norm(arm[1] - arm[0])
            if (
                length < 0.5 * fw
                or length > 3.7 * fw
                or np.linalg.norm(arm[2] - arm[1]) > 0.8 * length
            ):
                continue
            xi, yi = np.rint(arm).astype(int).T
            if (
                xi.min() < 0
                or yi.min() < 0
                or xi.max() >= labels.shape[1]
                or yi.max() >= labels.shape[0]
            ):
                continue
            # Thin wrists can land just outside the matte at network resolution.
            # Project to the nearest pixel of this person within a small radius.
            radius = max(2, round(0.23 * fw))
            for index, (px, py) in enumerate(zip(xi, yi)):
                if labels[py, px] == component:
                    continue
                x0, y0 = max(0, px - radius), max(0, py - radius)
                ys, xs = np.where(
                    labels[y0 : py + radius + 1, x0 : px + radius + 1] == component
                )
                if xs.size:
                    distances = (xs + x0 - px) ** 2 + (ys + y0 - py) ** 2
                    k = distances.argmin()
                    if distances[k] <= radius**2:
                        arm[index] = [xs[k] + x0, ys[k] + y0]
            xi, yi = np.rint(arm).astype(int).T
            if not np.all(labels[yi, xi] == component):
                continue
            # Require an exposed hand, away from faces, rather than dragging a
            # crossed arm, a hand against the chin or the neighboring subject.
            if any(
                np.linalg.norm(arm[2] - [bx + bw / 2, by + bh / 2]) < 1.05 * bh
                for bx, by, bw, bh in (f["box"] for f in faces)
            ):
                continue
            radius = max(3, round(0.42 * fw))
            near_hand = labels[
                max(0, yi[2] - radius) : yi[2] + radius + 1,
                max(0, xi[2] - radius) : xi[2] + radius + 1,
            ]
            if np.mean(near_hand == 0) < 0.10 or np.any(
                (near_hand != 0) & (near_hand != component)
            ):
                continue
            best = confidence
            face["arm"] = np.round(arm[[0, 2]].reshape(-1), 2).tolist()


def analyze_art(path):
    import cv2

    with Image.open(path) as image:
        rgba = np.asarray(ImageOps.exif_transpose(image).convert("RGBA"))
    h, w = rgba.shape[:2]
    if min(h, w) < 40:
        return None
    # Neutral backdrop prevents invisible RGB from becoming a detected face.
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255
    rgb = np.uint8(rgba[:, :, :3] * alpha + 160 * (1 - alpha))
    scale = min(960 / max(w, h), 2)
    dw, dh = max(1, round(w * scale)), max(1, round(h * scale))
    small = cv2.resize(rgb, (dw, dh), interpolation=cv2.INTER_AREA)
    detector = cv2.FaceDetectorYN.create(str(MODEL), "", (dw, dh), 0.82, 0.30)
    _, detections = detector.detect(cv2.cvtColor(small, cv2.COLOR_RGB2BGR))
    if detections is None:
        return None
    faces = []
    for row in detections:
        coords = row[:14].reshape(-1, 2) * [w / dw, h / dh]
        (x, y), (fw, fh), eye_a, eye_b, nose, *_ = coords
        if fw < 36 or fh < 38 or x < 0 or y < 0 or x + fw > w or y + fh > h:
            continue
        if rgba[int(nose[1].clip(0, h - 1)), int(nose[0].clip(0, w - 1)), 3] < 224:
            continue
        eyes = []
        distance = eye_b[0] - eye_a[0]
        if distance > 0.28 * fw and abs(eye_a[1] - eye_b[1]) < 0.27 * distance:
            eyes = [_eye(rgb, eye, fw) for eye in (eye_a, eye_b)]
            if all(eyes):
                a, b = eyes
                if (
                    b[0] - a[0] < 0.25 * fw
                    or abs(a[1] - b[1]) > 0.30 * (b[0] - a[0])
                    or min(a[3], b[3]) < 0.5 * max(a[3], b[3])
                    or min(a[2], b[2]) < 0.54 * max(a[2], b[2])
                    or min(a[3], b[3]) < 1.5
                ):
                    eyes = []
            else:
                eyes = []
        faces.append(
            {"box": [round(float(v), 2) for v in (x, y, fw, fh)], "eyes": eyes}
        )
    if not faces:
        return None
    _locate_free_arms(rgba, rgb, faces)
    seed = int.from_bytes(hashlib.sha256(rgba.tobytes()).digest()[:4], "big")
    return {"width": w, "height": h, "seed": seed, "faces": faces}


def prepare_scene_art(scenes, public, *, painted_poses=False):
    """Attach controls only to artwork actually drawn on eligible character shots."""
    cache = {}

    def attach(record, key, field, motion):
        path = record[key]
        if path not in cache:
            cache[path] = analyze_art(public / path)
        plan = cache[path]
        if plan and (motion != "eyes" or any(f["eyes"] for f in plan["faces"])):
            record[field] = {**plan, "motion": motion}

    for scene in scenes:
        if scene.get("subject") != "personagens":
            continue
        mode = scene.get("renderMode")
        if mode == "master_static":
            if scene["foreground"] == scene["background"]:
                attach(scene, "foreground", "foregroundPerformance", "portrait")
            else:
                attach(scene, "background", "backgroundPerformance", "portrait")
        elif mode == "multilayer":
            for layer in scene.get("layers", []):
                if layer["role"] not in (
                    "character",
                    "front_character",
                    "back_character",
                ):
                    continue
                rig = layer.get("rigFrames")
                if painted_poses and rig:
                    variants = {}
                    for src in rig["frames"]:
                        variant = {"src": src}
                        attach(variant, "src", "performance", "cutout")
                        if "performance" in variant:
                            variants[src] = variant["performance"]
                    if variants:
                        layer["posePerformances"] = variants
                if layer.get("meshFrames") or rig:
                    continue  # Existing authored animation takes precedence.
                risky = (
                    layer.get("heroRisk", 0) > 0.04
                    or layer.get("contactRisk", 0) > 0.1
                    or any(item["role"] == "hero_prop" for item in scene["layers"])
                )
                attach(layer, "src", "performance", "eyes" if risky else "cutout")
        elif mode == "2_5d":
            attach(scene, "foreground", "foregroundPerformance", "cutout")
