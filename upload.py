#!/usr/bin/python

# upload.py
# In: Name of directory, date of airing, and when to publish

import os
import fnmatch
import sys
import json
import time
import requests

from requests_toolbelt.multipart.encoder import MultipartEncoder
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

MIXCLOUD_ACCESS_KEY = os.getenv('MIXCLOUD_ACCESS_KEY')
FOLDER_SKIP = os.getenv('FOLDER_SKIP')

# Assumptions:
# - There is one .mp3 in each subdirectory of a show
# - There is one .jpg in each subdirectory for a show

# Send POST Request to Mixcloud with passed data
# Returns: Int
def send_post_request(data):
    response = requests.post(MIXCLOUD_ACCESS_KEY, data=data, headers={'Content-Type': data.content_type})
    # Debug
    print(response.json())
    if response.status_code != 200:
        return response.json()["error"]["retry_after"] + 10
    else :
        return 0

# Takes passed data and 
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

def main():

    # Handle flags
    # Bypass input (for testing):
    if sys.argv[1] == '--bypass':
        target_dir = 'SHOW 2'
        mixcloud_airdate = '5th August 2021'
        publish_date = '2021-08-23'
        publish_time = '00:00:00'
    else:
        target_dir = raw_input("Enter target directory: ")
        mixcloud_airdate = raw_input("Enter airing date (ex: 1st January 2022): ")
        mixcluoud_publish_date = raw_input("Enter publish date (YYYY-MM-DD): ")
        mixcloud_publish_time = raw_input("Enter publish time (UTC Time HH:MM:SS): ")

    encoder_queue = []

    # Example directory:
    # London Show 4 (target_dir)
    # -- DJ Elephant (artist_dir)
    # -- The Podcast Show (artist_dir)
    # -- The Band (artist_dir)
    # -- Talk show (artist_dir)

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

                encoder_data = create_show_request(artist_dir, mixcloud_airdate, root, publish_date, publish_time)
                encoder_queue.append(encoder_data)


    # Traverse queue and execute requests
    for x in encoder_queue:
        successful = False
        while not successful:
            print('Trying a request: ')
            print(x)
            response = send_post_request(x)
            if response != 0:
                print('Response is an error')
                print('Resetting after sleeping for ' + str(response) + ' seconds')
                time.sleep(response)
            else:
                print('Sucessfully uploaded!')
                break


if __name__ == "__main__":
    main()
