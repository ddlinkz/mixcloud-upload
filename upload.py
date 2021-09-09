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
#############

# Load .env variables
load_dotenv()

MIXCLOUD_ACCESS_KEY = os.getenv('MIXCLOUD_ACCESS_KEY')
FOLDER_SKIP = os.getenv('FOLDER_SKIP')
WORKING_DIR = os.getenv('WORKING_DIR')

# Flags class for easier readability
class Flags:
    """Flags class for passing between functions"""
    def __init__(self):
        self.embed = False
        self.target = ''
        self.airdate = ''
        self.pdate = ''
        self.ptime = ''

    def set_embed(self, boolean):
        self.embed = boolean

    def set_target(self, target):
        self.target = target

    def set_airdate(self, airdate):
        self.airdate = airdate

    def set_pdate(self, pdate):
        self.pdate = pdate

    def set_ptime(self, ptime):
        self.ptime = ptime

# Handles flags
# Returns: Flags type
def handle_flags(flags):
    f = Flags()
    if '--usage' in flags:
        print('--bypass: Inputs are automatically filled for testing')
        print('--embed: Writes file embedcodt.txt that contains embed HTML for each Mixcloud mix')
        quit()
    if '--embed' in flags:
        print('Exporting embeds at the end of upload...')
        f.set_embed(True)
    # Bypass input (for testing):
    if '--bypass' in flags:
        week_later_date = datetime.datetime.today() + datetime.timedelta(days=7)

        f.set_target('SHOW2')
        f.set_airdate('TEST TEST')
        f.set_pdate(week_later_date.strftime('%Y-%m-%d'))
        f.set_ptime('00:00:00')
    else:
        f.set_target(raw_input("Enter target directory: "))
        f.set_airdate(raw_input("Enter airing date (ex: 1st January 2022): "))
        f.set_pdate(raw_input("Enter publish date (YYYY-MM-DD): "))
        f.set_ptime(raw_input("Enter publish time (UTC Time HH:MM:SS): "))
    return f

# Send POST Request to Mixcloud with passed data
# Returns: Reponse obj
def send_post_request(data):
    response = requests.post(MIXCLOUD_ACCESS_KEY, 
                             data=data, 
                             headers={'Content-Type': data.content_type}, 
                             timeout=180)
    return response

# Takes passed data and returns an encoder obj
# Returns: MultipartEncoder object
def create_show_request(artist, airdate, root, date, time):
    showname_title = "{0} for SNS - {1} ".format(artist, airdate)
    path_to_show = "{0}/{1}".format(root, artist)
    publish_str = "{0}T{1}Z".format(date, time)

    print("Attempting encode for " + showname_title + " in " + artist)
    mp3, jpg = locate_filenames(path_to_show)
    if mp3 is None:
        return None

    # Create requests data
    m = MultipartEncoder(
        fields={
            'mp3': ('track.mp3', open("{0}/{1}".format(path_to_show, mp3), 'rb'), 'text/plain'),
            'picture': ('picture.jpg', open("{0}/{1}".format(path_to_show, jpg), 'rb')),
            'name': showname_title, 
            'description': "{0} for SNS.".format(artist), 
            'publish_date': publish_str,
            }
        )
    return m

# Takes in an array of dicts, encodes each one then sends a request
# Returns an array of modified dicts and array of dict keys
# Returns: Arr, Arr
def process_queue(request_queue):
    remain = []
    success = []

    # Traverse queue and execute requests
    for post_request_data in request_queue:
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

        print('Trying a POST request to Mixcloud... ')

        print(post_request_encoder)

        response = send_post_request(post_request_encoder)

        # Debug
        print(response.json())

        if response.status_code != 200:
            print('Response is an error!')
            if "retry_after" not in response.json()["error"]:
                print('Something is wrong with the data.')
                print('Can\'t retry this... here\'s what it says:')
                print(response.json())
                continue

            retry_time = response.json()["error"]["retry_after"]
            print('Response is an error!')
            print('Trying this request later...')

            # Modify data before appending, this is so the request will be accepted by the server
            new_time = datetime.datetime.strptime(post_request_data.pop("time"), '%H:%M:%S') + datetime.timedelta(minutes=2)
            new_post_request_data = post_request_data
            new_post_request_data["time"] = new_time.strftime('%H:%M:%S')
            remain.append(new_post_request_data)

            print('Resetting after sleeping for {0} seconds'.format(str(retry_time)))
            wait_progress_bar(retry_time)
        else:
            print('Sucessfully uploaded!')
            success.append(response.json()["result"]["key"])

    return remain, success

# Given path, walks through directory to find files, which are only allowed 1 of
# Returns: String tuple, None if files are invalid
def locate_filenames(path):
    # Walk through the given path to find files
    for _, _, potential_files in os.walk(path):

        # Filters used for matching
        mp3_file_filter = fnmatch.filter(potential_files, '*.mp3')
        jpg_file_filter = fnmatch.filter(potential_files, '*.jpg')

        if len(mp3_file_filter) != 1:
            print('Can\'t find .mp3 for show (check folder for only 1 .mp3)')
            return None, None
        if len(jpg_file_filter) != 1:
            print('Can\'t find .jpg for show (check folder for only 1 .mp3)')
            return None, None

        mp3_fn = mp3_file_filter[0]
        jpg_fn = jpg_file_filter[0]

        print('Using audio file: {0}'.format(mp3_fn))
        print('Using file: {0}'.format(jpg_fn))

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

# Given a key, returns the string for an iframe
# Returns: Str
def get_iframe(key):
    src = "https://www.mixcloud.com/widget/iframe/?feed=" + key.replace("/", "%2F")
    width = '\"100%\"'
    height = '\"400\"'
    frameborder = '\"0\"'
    return "<iframe width={0} height={1} {2} frameborder={3} ></iframe> \n".format(width,
                                                                                   height, 
                                                                                   src, 
                                                                                   frameborder)

def main():
    print("Moving to: {0}".format(WORKING_DIR))
    try:
        os.chdir(WORKING_DIR)
    except Error:
        print('Moving to {0} resulted in an error.'.format(WORKING_DIR))

    flags = handle_flags(sys.argv[1:])
    validate_inputs(flags.pdate, flags.ptime)

    encoder_queue = []

    # Traverse directory tree starting from root in search for target_dir
    for root, dirs, _ in os.walk("."):
        path = root.split(os.sep)

        # If root (current dir) = target_dir, found it
        if(os.path.basename(root) == flags.target):
            print('Found your target directory...: {0}'.format(flags.target))

            # Create request encoding for each show
            for artist_dir in dirs:

                # Skip dirs (if neccessary)
                if artist_dir in FOLDER_SKIP:
                    continue

                entry = create_show_request_entry(artist_dir, 
                                                  flags.airdate, 
                                                  root, 
                                                  flags.pdate, 
                                                  flags.ptime)
                encoder_queue.append(entry)

    # Process queue for the first time
    remaining_queue, success_list = process_queue(encoder_queue)

    # If there are any shows remaining, continue to process
    while(len(remaining_queue) != 0):
        remaining_queue, success = process_queue(remaining_queue)
        success_list.extend(success)

    print('Uploaded {0} show(s) from {1}!'.format(str(len(success_list)), flags.target))

    # Store HTML embeds for future use if flag is turned on
    if flags.embed:
        print('Storing HTML iframe embeds in embedcode.txt...')
        with open('embedcode.txt', 'w') as file:
            for key in success_list:
                file.write(get_iframe(key))

if __name__ == "__main__":
    main()
