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

MIXCLOUD_ACCESS_KEY = os.getenv('MIXCLOUD_ACCESS_KEY')
FOLDER_SKIP = os.getenv('FOLDER_SKIP')

mp3pattern = '*.mp3'
jpgpattern = '*.jpg'

# Assumptions:
# - There is one .mp3 in each subdirectory of a show
# - There is one .jpg in each subdirectory for a show

def upload_request(data):
    r = requests.post(, data=data, headers={'Content-Type': data.content_type})
    r_json = r.json()
    print(r_json)
    if r.status_code != 200:
        return r_json["error"]["retry_after"] + 10
    else :
        return 0

def main():

    # Handle flags
    if sys.argv[1] == '-t':
        target = 'SHOW 2'
        airdate = '5th August 2021'
        publish_date = '2021-08-23'
        publish_time = '00:00:00'
    else:
        target = raw_input("Enter target directory: ")
        airdate = raw_input("Enter airing date (ex: 1st January 2022): ")
        publish_date = raw_input("Enter publish date (YYYY-MM-DD): ")
        publish_time = raw_input("Enter publish time (UTC Time HH:MM:SS): ")

    encoderQueue = []

    for root, dirs, files in os.walk("."):
        path = root.split(os.sep)

        # Find directory
        if(os.path.basename(root) == target):
            print('Found it!')

            # Take each dirs, concat to root, dir = artist name
            for artist in dirs:

                # Skip dirs (if neccessary)
                if artist == FOLDER_SKIP:
                    continue

                # Form data
                showname_str = artist + " for SNS - " + airdate
                path_to_show = root + "/" + artist
                publish_str = publish_date + "T" + publish_time + "Z"

                print("Uploading " + showname_str + " in " + os.path.basename(path_to_show))
                for root2, dirs2, files2 in os.walk(path_to_show):
                    for filename in fnmatch.filter(files2, mp3pattern):
                        print('Uploading file! ' + filename)
                    for picname in fnmatch.filter(files2, jpgpattern):
                        print('Uploading pic! ' + picname)

                # Create requests data
                m = MultipartEncoder(
                    fields={
                        'mp3': ('track.mp3', open(path_to_show+"/"+filename, 'rb'), 'text/plain'),
                        'picture': ('picture.jpg', open(path_to_show+"/"+picname, 'rb')),
                        'name':showname_str, 
                        'description': artist + " for SNS.", 
                        'publish_date':publish_str,
                        }
                    )

                encoderQueue.append(m)


    # Traverse queue and execute requests
    for x in encoderQueue:
        successful = False
        while not successful:
            print('Trying a request: ')
            print(x)
            response = upload_request(x)
            if response != 0:
                print('Response is an error')
                print('Resetting after sleeping for ' + str(response) + ' seconds')
                time.sleep(response)
            else:
                print('Sucessfully uploaded!')
                break


if __name__ == "__main__":
    main()
