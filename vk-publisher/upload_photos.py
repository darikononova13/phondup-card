"""Upload images to VK community wall using an administrator user token.

Security: all tokens come from GitHub Actions secrets. Never log raw API response
or upload URLs, since they may contain private information.
"""
import json
import mimetypes
import os
import urllib.parse
import urllib.request
from pathlib import Path

API_VERSION = "5.199"
MEDIA_DIR = (Path.cwd() / "vk-publisher" / "media").resolve()
MAX_BYTES = 10 * 1024 * 1024


def call_vk(method, token, **params):
    body = urllib.parse.urlencode(
        dict(params, access_token=token, v=API_VERSION)
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.vk.com/method/" + method,
        data=body,
        method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            data = json.load(response)
    except Exception as exc:
        raise RuntimeError("Could not reach VK API for image upload") from None
    if not isinstance(data, dict):
        raise RuntimeError("VK did not return a valid API response")
    if "error" in data:
        error = data["error"]
        code = error.get("error_code", "unknown")
        raise RuntimeError("VK image upload API rejected {} (error code {}). Check administrator user token and permissions.".format(method, code))
    return data.get("response")


def safe_image_path(value):
    if not isinstance(value, str) or not value.startswith("vk-publisher/media/"):
        raise ValueError("Image must be a file in vk-publisher/media/")
    path = (Path.cwd() / value).resolve()
    if not path.is_relative_to(MEDIA_DIR) or not path.is_file():
        raise ValueError("Image does not exist in permitted media directory")
    if path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        raise ValueError("Only JPG or PNG images are supported")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Image is too large: 10 MB limit")
    if path.stat().st_size < 100:
        raise ValueError("Image is empty or invalid")
    return path


def upload_image(path, group_id, user_token):
    upload = call_vk("photos.getWallUploadServer", user_token, group_id=group_id)
    upload_url = upload.get("upload_url") if isinstance(upload, dict) else None
    if not isinstance(upload_url, str) or urllib.parse.urlsplit(upload_url).scheme != "https":
        raise RuntimeError("VK did not return an HTTPS upload server URL")
    filedata = path.read_bytes()
    boundary = "PHONDUPVKPHOTOBOUNDARY"
    mimetype = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    body = (
        ("--" + boundary + "\r\n" +
         'Content-Disposition: form-data; name="photo"; filename="post-image' +
         path.suffix.lower() + '"\r\n' +
         "Content-Type: " + mimetype + "\r\n\r\n").encode()
         + filedata + ("\r\n--" + boundary + "--\r\n").encode()
    )
    request = urllib.request.Request(
        upload_url,
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
        method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=80) as resp:
            uploaded = json.load(resp)
    except Exception:
        raise RuntimeError("VK upload server rejected the image bytes") from None
    if not isinstance(uploaded, dict) or not all(k in uploaded for k in ("photo", "server", "hash")):
        raise RuntimeError("VK photo upload returned incomplete data")
    saved = call_vk(
        "photos.saveWallPhoto", user_token,
        group_id=group_id,
        photo=uploaded["photo"],
        server=uploaded["server"],
        hash=uploaded["hash"]
    )
    if not isinstance(saved, list) or not saved:
        raise RuntimeError("VK did not save the wall photo")
    photo = saved[0]
    owner, pid = photo.get("owner_id"), photo.get("id")
    if not isinstance(owner, int) or not isinstance(pid, int):
        raise RuntimeError("VK did not return a valid saved photo ID")
    print("A photo was uploaded and saved successfully.")
    return "photo{}_{}".format(owner, pid)


def upload_images(items, group_id, token):
    if not isinstance(items, list) or not 1 <= len(items) <= 5:
        raise ValueError("images must be an array of 1 to 5 relative paths")
    if not token:
        raise RuntimeError(
            "Photo publishing needs a separate administrator OAuth user token "
            "in GitHub Actions secret VK_USER_TOKEN. "
            "Do not paste it into chat or code."
        )
    # Validate all local files before making any network calls.
    files = [safe_image_path(p) for p in items]
    result = []
    for photo in files:
        result.append(upload_image(photo, group_id, token))
    return result
