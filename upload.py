#!/usr/bin/python
# upload.py

import os
import fnmatch
import sys
import json
import time
import requests
import random
import datetime
from alive_progress import alive_bar

from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from dotenv import load_dotenv

#############
# Todo:
# - Progress bar for uploading + for waiting
# - Response code testing
#############

# Load .env variables
load_dotenv()

MIXCLOUD_ACCESS_KEY = os.getenv('MIXCLOUD_ACCESS_KEY')
FOLDER_SKIP = os.getenv('FOLDER_SKIP')

# Handles flags
# Returns: Str, Str, Str, Str
def handle_flags(flags):
    embed_flag = False
    if '--usage' in flags:
        print('--bypass: Inputs are automatically filled for testing')
        print('--embed X: Export ')
        quit()
    if '--embed' in flags:
        print('Exporting embeds at the end of upload...')
        embed_flag = True
    # Bypass input (for testing):
    if '--bypass' in flags:
        target_dir = 'SHOW2'
        mixcloud_airdate = 'TEST TEST'
        week_later_date = datetime.datetime.today() + datetime.timedelta(days=7)
        mixcloud_publish_date = week_later_date.strftime('%Y-%m-%d')
        mixcloud_publish_time = '00:00:00'
    else:
        target_dir = raw_input("Enter target directory: ")
        mixcloud_airdate = raw_input("Enter airing date (ex: 1st January 2022): ")
        mixcloud_publish_date = raw_input("Enter publish date (YYYY-MM-DD): ")
        mixcloud_publish_time = raw_input("Enter publish time (UTC Time HH:MM:SS): ")
    return target_dir, mixcloud_airdate, mixcloud_publish_date, mixcloud_publish_time, embed_flag

# Send POST Request to Mixcloud with passed data
# Returns: Reponse obj
def send_post_request(data):
    response = requests.post(MIXCLOUD_ACCESS_KEY, data=data, headers={'Content-Type': data.content_type}, timeout=180)
    return response

# Takes passed data and returns an encoder obj
# Returns: MultipartEncoder object
def create_show_request(artist, airdate, root, date, time):
    showname_title = artist + " for SNS - " + airdate
    path_to_show = root + "/" + artist
    publish_str = date + "T" + time + "Z"

    print("Attempting encode for " + showname_title + " in " + artist)
    mp3, jpg = locate_filenames(path_to_show)
    if mp3 is None:
        return None

    # Create requests data
    m = MultipartEncoder(
        fields={
            'mp3': ('track.mp3', open(path_to_show + "/" + mp3, 'rb'), 'text/plain'),
            'picture': ('picture.jpg', open(path_to_show + "/" + jpg, 'rb')),
            'name': showname_title, 
            'description': artist + " for SNS.", 
            'publish_date': publish_str,
            }
        )
    return m

# Given path, walks through directory to find files, which are only allowed 1 of
# Returns: String tuple, None if files are invalid
def locate_filenames(path):
    # Walk through the given path to find files
    for _, _, potential_files in os.walk(path):

        # Filters used for matching
        mp3_file_filter = fnmatch.filter(potential_files, '*.mp3')
        jpg_file_filter = fnmatch.filter(potential_files, '*.jpg')

        if len(mp3_file_filter) == 0 or len(mp3_file_filter) > 2:
            print('Can\'t find .mp3 for show (check folder for only 1 .mp3)')
            return None, None
        if len(jpg_file_filter) == 0 or len(jpg_file_filter) > 2:
            print('Can\'t find .jpg for show (check folder for only 1 .mp3)')
            return None, None

        mp3_fn = mp3_file_filter[0]
        jpg_fn = jpg_file_filter[0]

        print('Using audio file: + ' + mp3_fn)
        print('Using file: ' + jpg_fn)

    return mp3_fn, jpg_fn


# Takes data and creates a dictionary entry
# Returns: Dictionary
def create_show_request_entry(artist, airdate, root, date, time):
    entry = {'artist': artist,
              'airdate': airdate,
              'root': root,
              'date': date,
              'time': time}
    return entry

# Validates data string, throws error if incorrect format
# Returns: None
def validate_date(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY-MM-DD")

# Validates time string, throws error if incorrect format
# Returns: None
def validate_time(time_text):
    try:
        datetime.datetime.strptime(time_text, '%H:%M:%S')
    except ValueError:
        raise ValueError("Incorrect data format, should be HH:MM:SS")

# Validates inputs
# Returns: None
def validate_inputs(date, time):
    validate_date(date)
    validate_time(time)

# Progress bar functions
# Returns: None
def wait_progress_bar(seconds):
    with alive_bar(seconds, spinner='notes') as bar:
        for i in range(seconds):
            time.sleep(1)
            bar()

# Callback for progress bar during request
def create_callback(encoder):
    encoder_len = len(encoder)
    bar = alive_bar(encoder_len)

    def callback(monitor):
        bar()

    return callback

# Given a key, output the string for an iframe
def get_iframe(key):
    src = "https://www.mixcloud.com/widget/iframe/?feed=" + key.replace("/", "%2F")
    return "<iframe width=\"100%\" height=\"400\"" + src + " frameborder=\"0\" ></iframe> \n"

def main():
    target_dir, mixcloud_airdate, mixcloud_publish_date, mixcloud_publish_time, embed_flag = handle_flags(sys.argv[1:])
    validate_inputs(mixcloud_publish_date, mixcloud_publish_time)

    print(embed_flag)

    # Example directory:
    # - root
    # ---London Show 4 (target_dir)
    # ---- DJ Elephant (artist_dir)
    # ---- The Podcast Show (artist_dir)
    # ---- The Band (artist_dir)
    # ---- Talk show (artist_dir)

    encoder_queue = []
    success_list = []

    # Traverse directory tree starting from root in search for target_dir
    for root, dirs, _ in os.walk("."):
        path = root.split(os.sep)

        # If root (current dir) = target_dir, found it
        if(os.path.basename(root) == target_dir):
            print('Found your target directory...: ' + target_dir)

            # Create request encoding for each show
            for artist_dir in dirs:

                # Skip dirs (if neccessary)
                if artist_dir in FOLDER_SKIP:
                    continue

                entry = create_show_request_entry(artist_dir, mixcloud_airdate, root, mixcloud_publish_date, mixcloud_publish_time)
                encoder_queue.append(entry)

    # Traverse queue and execute requests
    for post_request_data in encoder_queue:
        print('Encoding form data...')

        # Now, create request before sending
        post_request_encoder = create_show_request(post_request_data["artist"],
                                                   post_request_data["airdate"],
                                                   post_request_data["root"],
                                                   post_request_data["date"],
                                                   post_request_data["time"])

        if post_request_encoder is None:
            print('Show contained invalid file inputs. Check directory again.')
            continue

        print(post_request_encoder)

        print('Trying a POST request to Mixcloud... ')

        response = send_post_request(post_request_encoder)

        # Debug
        print(response.json())

        if response.status_code != 200:
            retry_time = response.json()["error"]["retry_after"]
            print('Response is an error!')
            print('Trying this request later...')

            # Modify data before appending, this is so the request will be accepted by the server
            new_time = datetime.datetime.strptime(post_request_data.pop("time"), '%H:%M:%S') + datetime.timedelta(minutes=2)
            post_request_data["time"] = new_time.strftime('%H:%M:%S')

            encoder_queue.append(post_request_data)
            print('Resetting after sleeping for ' + str(retry_time) + ' seconds')
            wait_progress_bar(retry_time)
        else:
            print('Sucessfully uploaded!')
            success_list.append(response.json()["result"]["key"])

    print('Uploaded ' + str(len(success_list)) + ' shows from ' + target_dir + '!')

    # Store HTML embeds for future use if flag is turned on
    if embed_flag:
        print('Storing HTML iframe embeds in embedcode.txt...')
        with open('embedcode.txt', 'w') as file:
            for key in success_list:
                file.write(get_iframe(key))

if __name__ == "__main__":
    main()
