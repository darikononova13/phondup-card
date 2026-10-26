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
        code = error.get("error_code", "?")
        hints = {
            5: "VK ne prinial token. Prover VK_ACCESS_TOKEN: polnyi kluch soobshchestva, bez probelov i kavychek.",
            15: "Nedostatochno prav. Prover dostup k stene soobshchestva.",
            27: "Metod nedostupen etomu tipu tokena.",
            6: "Slishkom mnogo zaprosov. Povtori pozhe.",
        }
        hint = hints.get(code, "Prover prava i tip tokena VK.")
        # Print a short, nonsecret diagnostic to the GitHub run summary.
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as result:
                result.write("### PHONDUP / VK API\n\n")
                result.write("**Kod oshibki VK: {}**\n\n".format(code))
                result.write("{}\n\n".format(hint))
                result.write("Publikatsii ne bylo.\n")
        raise RuntimeError("VK ERROR CODE: {}\nVK HINT: {}".format(code, hint))
    return data.get("response")

def get_group_id():
    group_id = os.environ.get("VK_GROUP_ID", "").strip()
    if not group_id.isdecimal() or int(group_id) <= 0:
        raise RuntimeError("Missing numeric VK_GROUP_ID repository variable; required for posting")
    return int(group_id)

def check_community_token(token):
    # groups.getById can reject a group token even when that token is valid.
    data = api("groups.getTokenPermissions", token)
    if not isinstance(data, dict):
        raise RuntimeError("VK did not return group-token permissions")
    raw = data.get("permissions", [])
    names = [item.get("name", "") if isinstance(item, dict) else item for item in raw]
    if "wall" not in names:
        raise RuntimeError("Token is valid, but no 'wall' permission: enable community wall access")
    print("VK community token accepted. Wall permission is enabled.")
    print("No content has been posted.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("post_file", nargs="?")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("VK_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Missing VK_ACCESS_TOKEN Actions secret")
    check_community_token(token)
    if args.check:
        print("Note: publication access has not yet been tested.")
        return
    gid = get_group_id()
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
