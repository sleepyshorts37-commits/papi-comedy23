import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_BASE = "https://api.upload-post.com/api"
STATE_PATH = Path("quota_state.json")


def load_state():
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_usage(value):
    if isinstance(value, dict):
        if "count" in value:
            return value
        for nested in value.values():
            found = find_usage(nested)
            if found:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = find_usage(nested)
            if found:
                return found
    return {}


def get_account(api_key):
    request = urllib.request.Request(
        f"{API_BASE}/uploadposts/me",
        headers={"Authorization": f"Apikey {api_key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"::error::Verification du compte Upload-Post impossible (HTTP {exc.code}).")
        raise SystemExit(1)
    except Exception as exc:
        print(f"::error::Verification du compte Upload-Post impossible ({type(exc).__name__}).")
        raise SystemExit(1)


def write_output(can_publish):
    value = "true" if can_publish else "false"
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"can_publish={value}\n")
    print(f"can_publish={value}")


def check_quota():
    api_key = os.environ.get("UPLOAD_POST_API_KEY")
    if not api_key:
        print("::error::Secret GitHub manquant : UPLOAD_POST_API_KEY.")
        raise SystemExit(1)

    account = get_account(api_key)
    plan = str(account.get("plan", "")).strip()
    plan_key = plan.lower()
    api_usage = find_usage(account)
    state = load_state()

    count = api_usage.get("count")
    limit = api_usage.get("limit") or state.get("limit")
    last_reset = api_usage.get("last_reset") or state.get("last_reset")

    if count is None:
        count = state.get("count")

    # Upload-Post documents 10 monthly uploads for Free/Default accounts.
    if limit is None and plan_key in {"free", "default"}:
        limit = 10

    # Its monthly counter resets 30 days after last_reset.
    if count is not None and last_reset:
        try:
            reset_at = datetime.fromisoformat(str(last_reset).replace("Z", "+00:00"))
            if reset_at.tzinfo is None:
                reset_at = reset_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= reset_at + timedelta(days=30):
                count = 0
                last_reset = datetime.now(timezone.utc).isoformat()
        except ValueError:
            pass

    if count is not None and limit is not None:
        count, limit = int(count), int(limit)
        state = {
            "count": count,
            "limit": limit,
            "last_reset": last_reset,
            "plan": plan or state.get("plan", "unknown"),
            "source": "Upload-Post API usage / last confirmed upload",
        }
        save_state(state)
        summary = f"Quota Upload-Post : {count}/{limit} uploads mensuels (plan {plan or 'inconnu'})."
        print(summary)
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with open(summary_path, "a", encoding="utf-8") as output:
                output.write(summary + "\n")
        if count >= limit:
            print(f"::warning::Quota mensuel atteint ({count}/{limit}). Generation et publication suspendues. Augmenter le forfait Upload-Post pour reprendre les envois.")
            write_output(False)
            return
        write_output(True)
        return

    # A paid plan is allowed to proceed; Upload-Post itself enforces its plan quota.
    if plan_key not in {"free", "default", ""}:
        print(f"::notice::Forfait {plan} detecte; les limites du forfait seront appliquees par Upload-Post.")
        write_output(True)
        return

    print("::warning::Impossible de lire le quota et aucun compteur local fiable n'est disponible. Publication suspendue par precaution.")
    write_output(False)


def parse_response(response):
    try:
        payload = response.json()
    except ValueError:
        raise SystemExit(f"Upload-Post a renvoye une reponse non JSON (HTTP {response.status_code}).")
    if response.status_code >= 400:
        message = payload.get("message") or payload.get("error_code") or "Erreur API"
        raise SystemExit(f"Upload-Post HTTP {response.status_code}: {message}")
    if payload.get("success") is False:
        message = payload.get("message") or payload.get("error_code") or "publication refusee"
        raise SystemExit(f"Upload-Post a refuse la publication : {message}")
    return payload


def youtube_result(payload):
    results = payload.get("results") or {}
    if isinstance(results, dict):
        return results.get("youtube") or {}
    return {}


def wait_for_completion(payload, api_key):
    status = str(payload.get("status", "")).lower()
    request_id = payload.get("request_id")
    if status not in {"pending", "queued", "processing", "in_progress"}:
        return payload
    if not request_id:
        raise SystemExit("Upload-Post indique un traitement en cours sans request_id; publication non confirmee.")

    import requests

    headers = {"Authorization": f"Apikey {api_key}", "Accept": "application/json"}
    for _ in range(30):
        time.sleep(10)
        response = requests.get(
            f"{API_BASE}/uploadposts/status",
            headers=headers,
            params={"request_id": request_id},
            timeout=30,
        )
        payload = parse_response(response)
        status = str(payload.get("status", "")).lower()
        if status in {"completed", "success"}:
            return payload
        if status in {"failed", "error"}:
            raise SystemExit("Upload-Post a termine le traitement avec un echec.")
    raise SystemExit("Delai depasse en attendant la confirmation de publication Upload-Post.")


def persist_usage(payload):
    usage = find_usage(payload)
    state = load_state()
    if usage.get("count") is not None:
        state["count"] = int(usage["count"])
    elif state.get("count") is not None:
        state["count"] = int(state["count"]) + 1
    if usage.get("limit") is not None:
        state["limit"] = int(usage["limit"])
    if usage.get("last_reset"):
        state["last_reset"] = usage["last_reset"]
    state.setdefault("plan", "Default")
    state["source"] = "Last confirmed Upload-Post response"
    save_state(state)


def publish(video_path, title):
    import requests

    api_key = os.environ.get("UPLOAD_POST_API_KEY")
    if not api_key:
        raise SystemExit("Secret GitHub manquant : UPLOAD_POST_API_KEY")
    if not Path(video_path).is_file():
        raise SystemExit("Fichier video introuvable.")

    run_id = os.environ.get("GITHUB_RUN_ID")
    if run_id:
        idempotency_key = f"papi-comedy-run-{run_id}"
    else:
        digest = hashlib.sha256(Path(video_path).read_bytes()).hexdigest()
        idempotency_key = f"papi-comedy-{digest}"

    headers = {
        "Authorization": f"Apikey {api_key}",
        "Idempotency-Key": idempotency_key,
        "Accept": "application/json",
    }
    description = (
        f"{title}. Sketch humoristique original de Papi Comedy.\n\n"
        "#Bouki #HumourSenegalais #Shorts"
    )
    data = [
        ("title", title[:100]),
        ("description", description),
        ("user", "P"),
        ("platform[]", "youtube"),
        ("privacyStatus", "public"),
        ("tags[]", "Bouki"),
        ("tags[]", "Humour"),
        ("tags[]", "Senegal"),
        ("tags[]", "Shorts"),
        ("async_upload", "true"),
    ]

    with open(video_path, "rb") as video:
        response = requests.post(
            f"{API_BASE}/upload",
            headers=headers,
            files={"video": (Path(video_path).name, video, "video/mp4")},
            data=data,
            timeout=(30, 600),
        )
    payload = parse_response(response)
    payload = wait_for_completion(payload, api_key)

    result = youtube_result(payload)
    if result.get("success") is False:
        raise SystemExit("Upload-Post signale un echec de publication YouTube.")
    post_id = result.get("post_id") or result.get("video_id")
    upload_status = str(result.get("youtube_upload_status") or result.get("status") or "").lower()
    if not post_id or (upload_status and upload_status not in {"uploaded", "published", "completed", "success"}):
        raise SystemExit("Upload-Post n'a pas fourni de confirmation YouTube avec identifiant de video.")

    persist_usage(payload)
    print(f"PUBLICATION YOUTUBE CONFIRMEE: https://www.youtube.com/watch?v={post_id}")
    print(f"YOUTUBE_VIDEO_ID: {post_id}")
    if result.get("youtube_processing_status"):
        print(f"YOUTUBE_PROCESSING_STATUS: {result['youtube_processing_status']}")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--check-quota":
        check_quota()
    elif len(sys.argv) == 3:
        publish(sys.argv[1], sys.argv[2])
    else:
        raise SystemExit("Usage: python publish.py --check-quota OR python publish.py VIDEO_PATH TITLE")
