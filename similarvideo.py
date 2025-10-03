import streamlit as st
import requests
from datetime import timedelta
import re

# -----------------------------
# YouTube API Key
# -----------------------------
API_KEY = "YOUR_API_KEY"   # <-- replace with your YouTube API Key
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

# -----------------------------
# Helper: Parse ISO8601 duration
# -----------------------------
def parse_duration(duration):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    hours, minutes, seconds = match.groups(default="0")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

# -----------------------------
# Helper: Extract Video ID
# -----------------------------
def extract_video_id(url: str):
    """
    Extracts video ID from YouTube URL (works for watch, youtu.be, and embed links).
    """
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",  # watch?v=xxxx, embed/xxxx, etc.
        r"youtu\.be/([0-9A-Za-z_-]{11})"    # short links
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🔎 Find Similar YouTube Videos by Niche")

# Input for video URL
video_url = st.text_input("Enter a YouTube Video Link:")

# Number of similar videos to fetch
max_results = st.number_input("Number of Similar Videos:", min_value=1, max_value=20, value=5)

if st.button("Find Similar Videos"):
    try:
        # Extract Video ID
        video_id = extract_video_id(video_url)
        if not video_id:
            st.error("❌ Could not extract video ID. Please enter a valid YouTube link.")
            st.stop()

        # -----------------------------
        # Fetch Original Video Details
        # -----------------------------
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": video_id,
            "key": API_KEY
        }
        response = requests.get(YOUTUBE_VIDEO_URL, params=params)
        data = response.json()

        if "items" not in data or not data["items"]:
            st.error("❌ Video not found. Please check the link.")
        else:
            video_info = data["items"][0]
            title = video_info["snippet"].get("title", "N/A")
            description = video_info["snippet"].get("description", "")
            duration_iso = video_info["contentDetails"].get("duration", "PT0M0S")
            duration = str(timedelta(seconds=parse_duration(duration_iso)))
            views = video_info["statistics"].get("viewCount", "0")

            st.subheader("📌 Original Video Details")
            st.markdown(
                f"**Title:** {title}\n\n"
                f"**Description:** {description[:200]}...\n\n"
                f"**Duration:** {duration}\n\n"
                f"**Views:** {views}\n\n"
                f"**URL:** [Watch Here]({video_url})"
            )

            # -----------------------------
            # Search for Similar Videos
            # -----------------------------
            search_params = {
                "part": "snippet",
                "q": title,  # use original title as keyword
                "type": "video",
                "maxResults": max_results,
                "key": API_KEY
            }
            search_response = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
            search_data = search_response.json()

            st.subheader("🎯 Similar Videos")
            if "items" in search_data:
                for item in search_data["items"]:
                    sim_title = item["snippet"]["title"]
                    sim_desc = item["snippet"]["description"][:200]
                    sim_url = f"https://www.youtube.com/watch?v={item['id']['videoId']}"

                    st.markdown(
                        f"**Title:** {sim_title}\n\n"
                        f"**Description:** {sim_desc}\n\n"
                        f"**URL:** [Watch Here]({sim_url})"
                    )
                    st.write("---")
            else:
                st.warning("⚠️ No similar videos found.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
