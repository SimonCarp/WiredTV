import pygame
import os
import time
import random
from datetime import datetime
from moviepy.editor import VideoFileClip, vfx, AudioFileClip
import numpy as np
from threading import Thread
import pickle
import ctypes

locdir = os.getcwd()
print(os.path.join(locdir, "Resources", "Media"))
# Initialize Pygame and mixer
pygame.init()
pygame.mixer.init()
icon = pygame.image.load('UI/Icon.png')
pygame.display.set_icon(icon)
pygame.display.set_caption("WIRED TV")

# Configuration
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
fullscreen = False
VIDEO_FOLDER = os.path.join(locdir, "Resources", "Media")
AD_FOLDER = os.path.join(locdir, "Resources", "Ads")
BUMPER_FOLDER = os.path.join(locdir, "Resources", "Bumpers")
STATE_FILE = "last_episode_state.pkl"
SCHEDULE_FILE = "daily_schedule.pkl"

# Fullscreen
def toggle_fullscreen():
    global fullscreen
    fullscreen = not fullscreen
    if fullscreen:
        pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),pygame.FULLSCREEN)
        pygame.mouse.set_visible(True)  # Hide the mouse cursor
    else:
        pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.mouse.set_visible(True)  # Show the mouse cursor

# Function to load media files from a specific folder
def get_media_files(folder_path):
    files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
             if f.endswith(('.mkv', '.mp4'))]
    return sorted(files, key=lambda x: int(''.join(filter(str.isdigit, x))))

# Function to get all folders in the VIDEO_FOLDER
def get_folders(base_path):
    return [os.path.join(base_path, f) for f in os.listdir(base_path) 
            if os.path.isdir(os.path.join(base_path, f))]

# Function to set the window title
def set_window_title(folder_name, video_name):
    video_name = video_name.replace(".mkv", "").replace(".mp4", "")
    folder_name = folder_name.replace(os.path.join("Resources", "Media"), "").replace(os.path.join("Resources", "Ads"), "")
    current_time = time.strftime("%H:%M", time.localtime())
    title = f"WIRED TV - {folder_name} - {video_name}"
    pygame.display.set_caption(title)


# Function to create moving CRT scanlines effect
def create_scanlines(width, height):
    scanlines = pygame.Surface((width, height), pygame.SRCALPHA)
    scanline_offset = 1
    # Generate scanlines with phase shift
    for y in range(scanline_offset, height, 2):  # Create lines with a phase offset
        pygame.draw.line(scanlines, (0, 0, 0, 50), (0, y), (width, y))
    
    return scanlines

# Function to play the video
def play_video(video_path, start_time=0):
    # Load and prepare the video clip
    clip = VideoFileClip(video_path).subclip(start_time)  # Video dimensions
    last_sync_check = time.time()

    # Create a Pygame window matching the video size
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Load frame image and effects
    frame_image_path = "D:/WiredTV/UI/Frame.png"
    frame_image = pygame.image.load(frame_image_path).convert_alpha()
    frame_image = pygame.transform.scale(frame_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    
    scanlines = create_scanlines(SCREEN_WIDTH, SCREEN_HEIGHT)

    clock = pygame.time.Clock()
    frame_duration = 0.99957 / clip.fps
    current_time = 0

    audio_thread = None
    if clip.audio:
        audio_thread = Thread(target=play_adjusted_audio, args=(clip.audio, start_time))
        audio_thread.start()

    try:
        while current_time < clip.duration:
            audio_timestamp = current_time
            frame_index = int(audio_timestamp * clip.fps)
            if frame_index < clip.reader.nframes:
                # Extract the current frame from the video
                frame = clip.get_frame(audio_timestamp)

                # Scale the video frame to fit the screen size (maintain aspect ratio)
                video_surface = pygame.surfarray.make_surface(np.rot90(frame))
                if not fullscreen == True:
                    video_surface = pygame.transform.scale(video_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
                else:
                    video_surface = pygame.transform.scale(video_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
                video_surface = pygame.transform.flip(video_surface, True, False)

                # Draw the video frame over the effects (below the custom frame)
                screen.blit(video_surface, (0, 0))

                # Create the moving scanlines effect
                scanlines = create_scanlines(SCREEN_WIDTH, SCREEN_HEIGHT)
                screen.blit(scanlines, (0, 0))

                # Draw the custom frame image as the foreground (on top of the video)
                screen.blit(frame_image, (0, 0))
                pygame.display.flip()

            current_time += frame_duration

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_f:
                        toggle_fullscreen()

            clock.tick(clip.fps)

    finally:
        clip.close()
        if audio_thread and audio_thread.is_alive():
            audio_thread.join()

    return True


# Function to play adjusted audio in a separate thread
def play_adjusted_audio(audio_clip, start_time=0):
    if not isinstance(audio_clip, AudioFileClip):
        raise TypeError("Expected audio_clip to be an AudioFileClip instance")

    # Ensure the audio starts at the correct position
    adjusted_audio = audio_clip
    adjusted_audio.preview()  # This will play audio from the specified start time
    adjusted_audio.close()

# Save and load functions for the schedule and state
def save_state(state):
    with open(STATE_FILE, 'wb') as file:
        pickle.dump(state, file)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'rb') as file:
            return pickle.load(file)
    return {}

def save_schedule(schedule, date):
    with open(SCHEDULE_FILE, 'wb') as file:
        pickle.dump({'date': date, 'schedule': schedule}, file)

def load_schedule():
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, 'rb') as file:
            data = pickle.load(file)
            return data['date'], data['schedule']
    return None, None

# Generate a schedule for episodes in a day, including bumpers and ads
def generate_daily_schedule(video_folders, bumper_files, ad_files, state, seed):
    random.seed(seed)
    schedule = []
    total_duration = 0

    while total_duration < 24 * 3600:
        episodes_to_play = random.randint(1,2)
        for _ in range(episodes_to_play):
            folder = random.choice(video_folders)
            media_files = get_media_files(folder)
            
            if not media_files:
                continue

            last_episode_index = state.get(folder, 0)
            if last_episode_index >= len(media_files):
                last_episode_index = 0

            video_path = media_files[last_episode_index]
            clip = VideoFileClip(video_path)
            video_duration = int(clip.duration)
            
            if total_duration + video_duration > 24 * 3600:
                break

            total_duration += video_duration
            schedule.append((folder, video_path, video_duration, "episode"))
            state[folder] = last_episode_index + 1

        if total_duration >= 24 * 3600:
            break

        bumper = random.choice(bumper_files)
        bumper_clip = VideoFileClip(bumper)
        bumper_duration = int(bumper_clip.duration)
        total_duration += bumper_duration
        schedule.append(("Bumper", bumper, bumper_duration, "bumper"))

        ads_to_play = random.randint(3, 5)
        for _ in range(ads_to_play):
            ad = random.choice(ad_files)
            ad_clip = VideoFileClip(ad)
            ad_duration = int(ad_clip.duration)
            total_duration += ad_duration
            schedule.append(("Ad", ad, ad_duration, "ad"))

        bumper = random.choice(bumper_files)
        bumper_clip = VideoFileClip(bumper)
        bumper_duration = int(bumper_clip.duration)
        total_duration += bumper_duration
        schedule.append(("Bumper", bumper, bumper_duration, "bumper"))

        ads_to_play = random.randint(3, 5)
        for _ in range(ads_to_play):
            ad = random.choice(ad_files)
            ad_clip = VideoFileClip(ad)
            ad_duration = int(ad_clip.duration)
            total_duration += ad_duration
            schedule.append(("Ad", ad, ad_duration, "ad"))

        bumper = random.choice(bumper_files)
        bumper_clip = VideoFileClip(bumper)
        bumper_duration = int(bumper_clip.duration)
        total_duration += bumper_duration
        schedule.append(("Bumper", bumper, bumper_duration, "bumper"))

    save_state(state)
    return schedule

# Determine the current position to start based on time of day
def get_starting_position(schedule):
    current_seconds = datetime.now().hour * 3600 + datetime.now().minute * 60 + datetime.now().second
    elapsed_seconds = 0

    for i, (folder_name, video_path, duration, item_type) in enumerate(schedule):
        if elapsed_seconds + duration > current_seconds:
            return i, current_seconds - elapsed_seconds
        elapsed_seconds += duration

    return 0, 0

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    video_folders = get_folders(VIDEO_FOLDER)
    bumper_files = get_media_files(BUMPER_FOLDER)
    ad_files = get_media_files(AD_FOLDER)
    state = load_state()

    today_date = datetime.now().strftime('%Y%m%d')
    saved_date, saved_schedule = load_schedule()

    if saved_date == today_date:
        schedule = saved_schedule
    else:
        schedule = generate_daily_schedule(video_folders, bumper_files, ad_files, state, int(today_date))
        save_schedule(schedule, today_date)

    start_index, start_second = get_starting_position(schedule)

    running = True
    while running:
        for i in range(start_index, len(schedule)):
            item_type = schedule[i][3]
            folder_name, video_path, video_duration = schedule[i][:3]
            
            if item_type == "episode":
                set_window_title(folder_name, os.path.basename(video_path))
                if not play_video(video_path, start_time=start_second if i == start_index else 0):
                    running = False
                    break
                start_second = 0

            elif item_type == "bumper":
                set_window_title("Bumper", os.path.basename(video_path))
                if not play_video(video_path):
                    running = False
                    break

            elif item_type == "ad":
                set_window_title("Ad", os.path.basename(video_path))
                if not play_video(video_path):
                    running = False
                    break
    
    
if __name__ == "__main__":
    main()