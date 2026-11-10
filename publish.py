import os
import sys
from upload_post import UploadPostClient

if len(sys.argv) != 3:
    raise SystemExit("Usage: python publish.py VIDEO_PATH TITLE")

api_key = os.environ.get("UPLOAD_POST_API_KEY")
if not api_key:
    raise SystemExit("Missing GitHub secret: UPLOAD_POST_API_KEY")

video_path, title = sys.argv[1], sys.argv[2]
client = UploadPostClient(api_key=api_key)

response = client.upload_video(
    video_path=video_path,
    title=title,
    user="P",
    platforms=["youtube"],
)

print("Upload-Post response:", response)
if isinstance(response, dict) and response.get("success") is False:
    raise SystemExit("Upload-Post reported a publication failure.")
if hasattr(response, "status_code") and response.status_code >= 400:
    raise SystemExit(f"Upload-Post HTTP error: {response.status_code}")
