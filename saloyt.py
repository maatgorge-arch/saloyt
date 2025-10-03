import streamlit as st
import requests
from datetime import datetime, timedelta
import re  # custom duration parser

# YouTube API Key
API_KEY = "AIzaSyCSU8V7jLlGXUWN4v9LuLkbqpC6GT2R1TA"
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

# Duration parser (replaces isodate for Streamlit.io compatibility)
def parse_duration(duration):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    hours, minutes, seconds = match.groups(default="0")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

# Streamlit App Title
st.title("YouTube Viral Topics Tool")

# Input Fields
days = st.number_input("Enter Days to Search (1-30):", min_value=1, max_value=30, value=5)

# Runtime input for minimum video duration
min_duration = st.number_input(
    "Enter Minimum Video Duration (minutes):", 
    min_value=1, max_value=300, value=20
)

# List of broader keywords
keywords = [
   "Life Million Years Ago","King Kong","Beauty","Prehistoric Girl","Survival","Primitive Girl",
   "Albino Gorilla","Spider-Man","Hulk","Joker","Supergirl","Thor","She-Hulk","Dinosaur",
   "Megalodon","Jungle Survival","Wild Survival","Ancient Humans","Early Humans","Human Evolution",
   "Marvel AI","Venom","Wonder Woman","Catwoman","Black Widow","Superhero Battle","Monster Battle",
   "Prehistoric Love Story","Gorilla and Girl","Jurassic World","KPOP Demon Hunters"
]

# Fetch Data Button
if st.button("Fetch Data"):
    try:
        # Calculate date range
        start_date = (datetime.utcnow() - timedelta(days=int(days))).isoformat("T") + "Z"
        all_results = []

        # Iterate over the list of keywords
        for keyword in keywords:
            st.write(f"Searching for keyword: {keyword}")

            # Define search parameters
            search_params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "order": "viewCount",
                "publishedAfter": start_date,
                "maxResults": 5,
                "key": API_KEY,
            }

            # Fetch video data
            response = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
            data = response.json()

            if "items" not in data or not data["items"]:
                st.warning(f"No videos found for keyword: {keyword}")
                continue

            videos = data["items"]
            video_ids = [video["id"]["videoId"] for video in videos if "id" in video and "videoId" in video["id"]]
            channel_ids = [video["snippet"]["channelId"] for video in videos if "snippet" in video and "channelId" in video["snippet"]]

            if not video_ids or not channel_ids:
                st.warning(f"Skipping keyword: {keyword} due to missing video/channel data.")
                continue

            # Fetch video statistics + duration
            stats_params = {
                "part": "statistics,contentDetails",
                "id": ",".join(video_ids),
                "key": API_KEY
            }
            stats_response = requests.get(YOUTUBE_VIDEO_URL, params=stats_params)
            stats_data = stats_response.json()

            if "items" not in stats_data or not stats_data["items"]:
                st.warning(f"Failed to fetch video statistics for keyword: {keyword}")
                continue

            # Fetch channel statistics
            channel_params = {"part": "statistics", "id": ",".join(channel_ids), "key": API_KEY}
            channel_response = requests.get(YOUTUBE_CHANNEL_URL, params=channel_params)
            channel_data = channel_response.json()

            if "items" not in channel_data or not channel_data["items"]:
                st.warning(f"Failed to fetch channel statistics for keyword: {keyword}")
                continue

            stats = stats_data["items"]
            channels = channel_data["items"]

            # Collect results with duration filter
            for video, stat, channel in zip(videos, stats, channels):
                try:
                    title = video["snippet"].get("title", "N/A")
                    description = video["snippet"].get("description", "")[:200]
                    video_url = f"https://www.youtube.com/watch?v={video['id']['videoId']}"
                    views = int(stat["statistics"].get("viewCount", 0))
                    subs = int(channel["statistics"].get("subscriberCount", 0))

                    # Duration filter (runtime input in minutes)
                    duration_iso = stat["contentDetails"].get("duration", "PT0M0S")
                    duration_seconds = parse_duration(duration_iso)

                    if subs < 3000 and duration_seconds >= min_duration * 60:
                        all_results.append({
                            "Title": title,
                            "Description": description,
                            "URL": video_url,
                            "Views": views,
                            "Subscribers": subs,
                            "Duration": str(timedelta(seconds=int(duration_seconds)))
                        })
                except Exception as e:
                    st.warning(f"Error parsing video data: {e}")

        # Display results
        if all_results:
            st.success(f"Found {len(all_results)} results (>{min_duration} min videos, <3000 subs)!")
            for result in all_results:
                st.markdown(
                    f"**Title:** {result['Title']}  \n"
                    f"**Description:** {result['Description']}  \n"
                    f"**URL:** [Watch Video]({result['URL']})  \n"
                    f"**Views:** {result['Views']}  \n"
                    f"**Subscribers:** {result['Subscribers']}  \n"
                    f"**Duration:** {result['Duration']}"
                )
                st.write("---")
        else:
            st.warning(f"No results found for channels with fewer than 3,000 subscribers and duration over {min_duration} minutes.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
