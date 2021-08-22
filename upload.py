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
# - Sanitize inputs
# - Progress bar for uploading + for waiting
# - extract filename and verify assumptions
# - timeout
#  ->>> Assumptions:
# - There is one .mp3 in each subdirectory of a show
# - There is one .jpg in each subdirectory for a show
#############

# Load .env variables
load_dotenv()

MIXCLOUD_ACCESS_KEY = os.getenv('MIXCLOUD_ACCESS_KEY')
FOLDER_SKIP = os.getenv('FOLDER_SKIP')

print(FOLDER_SKIP)
print(type(FOLDER_SKIP))

# Send POST Request to Mixcloud with passed data
# Returns: Reponse obj
def send_post_request(data):
    response = requests.post(MIXCLOUD_ACCESS_KEY, data=data, headers={'Content-Type': data.content_type})
    return response

# Takes passed data and returns an encoder obj
# Returns: MultipartEncoder object
def create_show_request(artist, airdate, root, date, time):
    showname_title = artist + " for SNS - " + airdate
    filepath_to_show = root + "/" + artist
    publish_str = date + "T" + time + "Z"

    mp3pattern = '*.mp3'
    jpgpattern = '*.jpg'

    print("Uploading " + showname_title + " in " + artist)
    for root2, dirs2, files2 in os.walk(filepath_to_show):
        for filename in fnmatch.filter(files2, mp3pattern):
            print('Uploading file! ' + filename)
        for picname in fnmatch.filter(files2, jpgpattern):
            print('Uploading pic! ' + picname)

    # Create requests data
    m = MultipartEncoder(
        fields={
            'mp3': ('track.mp3', open(filepath_to_show+"/"+filename, 'rb'), 'text/plain'),
            'picture': ('picture.jpg', open(filepath_to_show+"/"+picname, 'rb')),
            'name':showname_title, 
            'description': artist + " for SNS.", 
            'publish_date':publish_str,
            }
        )
    return m

# Takes data and creates a dictionary with 
def create_show_request_entry(artist, airdate, root, date, time):
    entry = {'artist': artist,
              'airdate': airdate,
              'root': root,
              'date': date,
              'time': time}
    return entry

# Validates data string, throws error if incorrect format
def validate_date(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY-MM-DD")

# Validates time string, throws error if incorrect format
def validate_time(time_text):
    try:
        datetime.datetime.strptime(time_text, '%H:%M:%S')
    except ValueError:
        raise ValueError("Incorrect data format, should be HH:MM:SS")

# Validates inputs
def validate_inputs(date, time):
    validate_date(date)
    validate_time(time)

# Progress bar functions
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

def main():
    # Handle flags
    # Bypass input (for testing):
    if '--usage' in sys.argv[1:]:
        print('--bypass: Inputs are automatically filled for testing')
        quit()
    elif '--bypass' in sys.argv[1:]:
        target_dir = 'SHOW 2'
        mixcloud_airdate = '5th August 2021'
        week_later_date = datetime.datetime.today() + datetime.timedelta(days=7)
        mixcloud_publish_date = week_later_date.strftime('%Y-%m-%d')
        mixcloud_publish_time = '00:00:00'
    else:
        target_dir = raw_input("Enter target directory: ")
        mixcloud_airdate = raw_input("Enter airing date (ex: 1st January 2022): ")
        mixcloud_publish_date = raw_input("Enter publish date (YYYY-MM-DD): ")
        mixcloud_publish_time = raw_input("Enter publish time (UTC Time HH:MM:SS): ")

    validate_inputs(mixcloud_publish_date, mixcloud_publish_time)

    encoder_queue = []

    # Example directory:
    # - root
    # ---London Show 4 (target_dir)
    # ---- DJ Elephant (artist_dir)
    # ---- The Podcast Show (artist_dir)
    # ---- The Band (artist_dir)
    # ---- Talk show (artist_dir)

    # Traverse directory tree starting from root in search for target_dir
    for root, dirs, files  in os.walk("."):
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
        print('Trying a POST request to Mixcloud: ')

        # Now, create request before sending
        post_request_encoder = create_show_request(post_request_data["artist"],
                                                   post_request_data["airdate"],
                                                   post_request_data["root"],
                                                   post_request_data["date"],
                                                   post_request_data["time"])

        print(post_request_encoder)

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

if __name__ == "__main__":
    main()
