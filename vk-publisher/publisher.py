"""Post approved PHONDUP VK wall publications. Never log tokens."""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

V = "5.199"
ATT = re.compile(r"^(?:photo|video|doc)-?\d+_\d+(?:_[A-Za-z0-9]+)?$")

def api(method, token, **kwargs):
    body = urllib.parse.urlencode({**kwargs, "v": V, "access_token": token}).encode()
    req = urllib.request.Request("https://api.vk.com/method/" + method, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            data = json.load(response)
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("Could not reach VK API") from None
    if "error" in data:
        error = data["error"]
        raise RuntimeError("VK API {} error {}: {}".format(method, error.get("error_code"), error.get("error_msg")))
    return data.get("response")

def get_group(token):
    data = api("groups.getById", token, group_ids="phondup")
    groups = data.get("groups", []) if isinstance(data, dict) else data
    if not isinstance(groups, list) or not groups or not groups[0].get("id"):
        raise RuntimeError("VK did not resolve the PHONDUP community")
    return int(groups[0]["id"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("post_file", nargs="?")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("VK_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("Missing VK_ACCESS_TOKEN Actions secret")
    gid = get_group(token)
    if args.check:
        print("VK community token verified for lookup: https://vk.com/club{}".format(gid))
        print("Note: wall.post capability has not yet been verified")
        return
    if not args.post_file:
        parser.error("post_file required")
    path = Path(args.post_file)
    if path.suffix != ".json" or not path.is_file():
        raise ValueError("Invalid post file")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("approved") is not True:
        raise ValueError("Post must be approved before publishing")
    msg = payload.get("message", "")
    media = payload.get("attachments", [])
    if not isinstance(msg, str) or len(msg) > 12000:
        raise ValueError("Invalid message")
    if not isinstance(media, list) or len(media) > 10 or not all(isinstance(a, str) and ATT.fullmatch(a) for a in media):
        raise ValueError("Invalid VK media IDs")
    if not msg.strip() and not media:
        raise ValueError("Cannot publish empty content")
    params = {"owner_id": -gid, "from_group": 1, "message": msg, "guid": path.stem}
    if media:
        params["attachments"] = ",".join(media)
    result = api("wall.post", token, **params)
    if not isinstance(result, dict) or not result.get("post_id"):
        raise RuntimeError("VK did not confirm publication")
    print("Published: https://vk.com/wall-{}_{}".format(gid, result["post_id"]))

if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError) as err:
        print("Error: {}".format(err), file=sys.stderr)
        sys.exit(1)
