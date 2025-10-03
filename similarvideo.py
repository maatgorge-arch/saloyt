import streamlit as st
import requests
from datetime import timedelta
import re
from collections import Counter

# -----------------------------
# Your YouTube API Key
# -----------------------------
API_KEY = "AIzaSyCSU8V7jLlGXUWN4v9LuLkbqpC6GT2R1TA"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

# -----------------------------
# Helpers
# -----------------------------
def parse_duration(duration_iso: str) -> int:
    """Parse ISO8601 duration (PT#H#M#S) to seconds."""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
    if not match:
        return 0
    hours, minutes, seconds = match.groups(default="0")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

def format_duration(seconds: int) -> str:
    """Format seconds to H:MM:SS (uses timedelta string)."""
    return str(timedelta(seconds=int(seconds)))

def extract_video_id(input_str: str) -> str | None:
    """
    Accepts either a plain 11-char video id or a URL and returns the id.
    If input is already the id, returns it.
    """
    s = input_str.strip()
    if re.fullmatch(r'[0-9A-Za-z_-]{11}', s):
        return s
    # Try common URL patterns
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',   # watch?v=..., /embed/..., /v/...
        r'youtu\.be\/([0-9A-Za-z_-]{11})'
    ]
    for p in patterns:
        m = re.search(p, s)
        if m:
            return m.group(1)
    return None

# small stopword list
STOPWORDS = {
    "that","this","with","from","they","their","about","these","there","which",
    "would","could","should","because","around","video","watch","youtube","your",
    "what","when","where","have","like","just","more","will","also","many","such"
}

def top_keywords_from_text(text: str, n: int = 5) -> list:
    """Return top n keyword tokens from text (simple frequency + stopword filter)."""
    tokens = re.findall(r'\w+', (text or "").lower())
    tokens = [t for t in tokens if len(t) > 3 and t not in STOPWORDS]
    if not tokens:
        return []
    counts = Counter(tokens)
    return [w for w, _ in counts.most_common(n)]

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🔎 Find Similar YouTube Videos (Paste video ID)")

st.markdown("**Instructions:** Paste only the *video ID* (11 characters), e.g. `z_DsmsBwAGM`. You may also paste a full URL and the app will extract the ID.")

video_input = st.text_input("Enter YouTube Video ID (or full URL):", "")
max_results = st.number_input("Number of similar videos to return:", min_value=1, max_value=20, value=6)

if st.button("Find Similar Videos"):
    if not video_input:
        st.error("Please paste a video ID or URL first.")
        st.stop()

    video_id = extract_video_id(video_input)
    if not video_id:
        st.error("Could not extract a valid 11-character YouTube video ID. Check input and try again.")
        st.stop()

    # Fetch original video details
    try:
        with st.spinner("Fetching original video details..."):
            params = {
                "part": "snippet,contentDetails,statistics",
                "id": video_id,
                "key": API_KEY
            }
            r = requests.get(YOUTUBE_VIDEO_URL, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        st.error(f"Error fetching video details: {exc}")
        st.stop()

    if "items" not in data or not data["items"]:
        st.error("Video not found. Please check the video ID and API key/quota.")
        st.stop()

    vid_info = data["items"][0]
    snippet = vid_info.get("snippet", {})
    content = vid_info.get("contentDetails", {})
    stats = vid_info.get("statistics", {})

    title = snippet.get("title", "N/A")
    description = snippet.get("description", "")
    tags = snippet.get("tags", []) or []
    duration_iso = content.get("duration", "PT0S")
    duration_secs = parse_duration(duration_iso)
    views = stats.get("viewCount", "0")
    channel_title = snippet.get("channelTitle", "Unknown")

    st.subheader("📌 Original Video")
    st.markdown(
        f"**Title:** {title}\n\n"
        f"**Channel:** {channel_title}\n\n"
        f"**Duration:** {format_duration(duration_secs)}  \n"
        f"**Views:** {views}  \n"
        f"**Video ID:** `{video_id}`  \n"
        f"**URL:** https://www.youtube.com/watch?v={video_id}\n\n"
        f"**Description (first 300 chars):**\n\n{description[:300]}..."
    )

    # Build query from title, description, tags
    keywords = [title]
    keywords += top_keywords_from_text(description, n=6)
    if tags:
        keywords += tags[:6]
    search_query = " ".join(dict.fromkeys(keywords))  # remove duplicates keeping order
    st.info(f"Searching using query: **{search_query[:200]}**")

    # Search for similar videos
    try:
        with st.spinner("Searching for similar videos..."):
            search_params = {
                "part": "snippet",
                "q": search_query,
                "type": "video",
                "maxResults": int(max_results),
                "key": API_KEY
            }
            sr = requests.get(YOUTUBE_SEARCH_URL, params=search_params, timeout=15)
            sr.raise_for_status()
            search_data = sr.json()
    except Exception as exc:
        st.error(f"Error during search: {exc}")
        st.stop()

    items = search_data.get("items", [])
    candidate_ids = [it["id"]["videoId"] for it in items if it.get("id", {}).get("videoId") and it["id"]["videoId"] != video_id]
    if not candidate_ids:
        st.warning("No similar videos found via the search query.")
        st.stop()

    # Fetch details for candidates
    try:
        with st.spinner("Fetching details for found videos..."):
            vid_params = {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(candidate_ids),
                "key": API_KEY
            }
            vr = requests.get(YOUTUBE_VIDEO_URL, params=vid_params, timeout=15)
            vr.raise_for_status()
            vids_data = vr.json()
    except Exception as exc:
        st.error(f"Error fetching candidate video details: {exc}")
        st.stop()

    found = vids_data.get("items", [])
    if not found:
        st.warning("No detailed info available for found videos.")
        st.stop()

    st.subheader("🎯 Similar Videos")
    for v in found:
        vid_id = v["id"]
        vsn = v.get("snippet", {})
        vcd = v.get("contentDetails", {})
        vst = v.get("statistics", {})

        vt = vsn.get("title", "N/A")
        vch = vsn.get("channelTitle", "Unknown")
        vdesc = vsn.get("description", "")[:250]
        vviews = vst.get("viewCount", "0")
        vdur = format_duration(parse_duration(vcd.get("duration", "PT0S")))
        vurl = f"https://www.youtube.com/watch?v={vid_id}"

        st.markdown(
            f"**{vt}**  \n"
            f"Channel: {vch}  \n"
            f"Duration: {vdur}  •  Views: {vviews}  \n"
            f"URL: {vurl}  \n\n"
            f"{vdesc}"
        )
        st.write("---")

    st.success("Done — similar videos listed above.")
