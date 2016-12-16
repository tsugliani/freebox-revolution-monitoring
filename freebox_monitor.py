#!/usr/bin/env python
# pylint: disable=C0103,C0111,W0621
from __future__ import print_function

#
# Freebox API SDK / Docs: http://dev.freebox.fr/sdk/os/login/
#

import os
import json
import hmac
import time
import argparse
import ConfigParser
import sys

from hashlib import sha1
import requests

VERSION = "0.4.3"
ENDPOINT = "http://mafreebox.freebox.fr/api/v3"


def get_challenge(freebox_app_id):
    api_url = '%s/login/authorize/%s' % (ENDPOINT, freebox_app_id)

    r = requests.get(api_url)

    if r.status_code == 200:
        return r.json()
    else:
        print("Failed request: %s\n" % r.text)


def open_session(password, freebox_app_id):
    api_url = '%s/login/session/' % ENDPOINT

    app_info = {
        'app_id': freebox_app_id,
        'password': password
    }
    json_payload = json.dumps(app_info)

    r = requests.post(api_url, data=json_payload)

    if r.status_code == 200:
        return r.json()
    else:
        print("Failed request: %s\n" % r.text)


def get_connection_stats(headers):
    api_url = '%s/connection/' % ENDPOINT

    r = requests.get(api_url, headers=headers)

    if r.status_code == 200:
        return r.json()
    else:
        print("Failed request: %s\n" % r.text)


def get_ftth_status(headers):
    api_url = '%s/connection/ftth/' % ENDPOINT

    r = requests.get(api_url, headers=headers)

    if r.status_code == 200:
        return r.json()
    else:
        print('Failed request: %s\n' % r.text)


def get_and_print_metrics(creds):
    freebox_app_id = "fr.freebox.seximonitor"

    # Fetch challenge
    resp = get_challenge(creds['track_id'])
    challenge = resp['result']['challenge']

    # Generate session password
    h = hmac.new(creds['app_token'], challenge, sha1)
    password = h.hexdigest()

    # Fetch session_token
    resp = open_session(password, freebox_app_id)
    session_token = resp['result']['session_token']

    # Setup headers with the generated session_token
    headers = {
        'X-Fbx-App-Auth': session_token
    }

    # Setup hashtable for results
    myData = {}

    # Fetch connection stats
    jsonRaw = get_connection_stats(headers)

    # Generic datas, same for FFTH or xDSL
    myData['bytes_down'] = jsonRaw['result']['bytes_down']
    myData['bytes_up'] = jsonRaw['result']['bytes_up']
    myData['rate_down'] = jsonRaw['result']['rate_down']
    myData['rate_up'] = jsonRaw['result']['rate_up']
    if jsonRaw['result']['state'] == "up":
        myData['state'] = 1
    else:
        myData['state'] = 0

    # ffth for FFTH (default)
    # xdsl for xDSL
    connection_media = jsonRaw['result']['media']

    ###
    # FFTH specific
    if connection_media == "ffth":
        jsonRaw = get_ftth_status(headers)

        myData['sfp_pwr_rx'] = jsonRaw['result']['sfp_pwr_rx']
        myData['sfp_pwr_tx'] = jsonRaw['result']['sfp_pwr_tx']

    ###
    # xDSL specific
    if connection_media == "xdsl":
        pass

    # Prepping Graphite Data format
    timestamp = int(time.time())

    # Output the information
    print("freebox.bytes_down %s %d" % (myData['bytes_down'], timestamp))
    print("freebox.bytes_up %s %d" % (myData['bytes_up'], timestamp))
    print("freebox.rate_down %s %d" % (myData['rate_down'], timestamp))
    print("freebox.rate_up %s %d" % (myData['rate_up'], timestamp))
    print("freebox.state %s %d" % (myData['state'], timestamp))
    if connection_media == "ffth":
        print("freebox.sfp_pwr_rx %s %d" % (myData['sfp_pwr_rx'], timestamp))
        print("freebox.sfp_pwr_tx %s %d" % (myData['sfp_pwr_tx'], timestamp))
    if connection_media == "xdsl":
        pass


def get_auth():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    cfg_file = os.path.join(script_dir, ".credentials")

    f = ConfigParser.RawConfigParser()
    f.read(cfg_file)

    try:
        _ = f.get("general", "track_id")
        _ = f.get("general", "app_token")
    except ConfigParser.NoSectionError as err:
        print("Config is invalid, auth not done.")
        return None

    return {'track_id': f.get('general', 'track_id'),
            'app_token': f.get('general', 'app_token')}


def write_auth(auth_infos):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    cfg_file = os.path.join(script_dir, ".credentials")
    f = ConfigParser.RawConfigParser()
    f.add_section("general")
    f.set("general", "track_id", auth_infos['track_id'])
    f.set("general", "app_token", auth_infos["app_token"])
    with open(cfg_file, "wb") as authFile:
        f.write(authFile)


def do_register(creds):
    if creds is not None:
        if 'track_id' in creds and 'app_token' in creds:
            print("Already registered, exiting")
            return

    print("Doing registration")
    headers = {'Content-type': 'application/json'}
    app_info = {
        'app_id': 'fr.freebox.seximonitor',
        'app_name': 'SexiMonitor',
        'app_version': VERSION,
        'device_name': 'SexiServer'
    }
    json_payload = json.dumps(app_info)

    r = requests.post('%s/login/authorize/' % ENDPOINT, headers=headers, data=json_payload)
    register_infos = None

    if r.status_code == 200:
        register_infos = r.json()
    else:
        print('Failed registration: %s\n' % r.text)

    write_auth(register_infos['result'])
    print("Don't forget to accept auth on the Freebox panel !")


def register_status(creds):
    if not creds:
        print("Status: invalid config, auth not done.")
        print("Please run `%s --register` to register app." % sys.argv[0])
        return
    print("Status: auth already done")
    print("  track_id: %s" % creds["track_id"])
    print("  app_token: %s" % creds["app_token"])


# Main
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--register', action='store_true', help="Register app with Freebox API")
    parser.add_argument('-s', '--register-status', dest='status', action='store_true', help="Get register status")
    args = parser.parse_args()

    auth = get_auth()

    if args.register:
        do_register(auth)
    elif args.status:
        register_status(auth)
    else:
        get_and_print_metrics(auth)