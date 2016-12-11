#!/usr/bin/env python
# pylint: disable=C0103,C0111,W0621


#
# Freebox API SDK / Docs: http://dev.freebox.fr/sdk/os/login/
#

import os
import json
import hmac
import time

from hashlib import sha1
import requests


def get_challenge(freebox_app_id):
    api_url = 'http://mafreebox.freebox.fr/api/v3/login/authorize/%s' % freebox_app_id

    r = requests.get(api_url)

    if r.status_code == 200:
        return r.json()
    else:
        print 'Failed request: %s\n' % r.text

def open_session(password, freebox_app_id):
    api_url = 'http://mafreebox.freebox.fr/api/v3/login/session/'

    app_info = {
        'app_id': freebox_app_id,
        'password': password
    }
    json_payload = json.dumps(app_info)

    r = requests.post(api_url, data=json_payload)

    if r.status_code == 200:
        return r.json()
    else:
        print 'Failed request: %s\n' % r.text



def get_connection_stats(headers):
    api_url = 'http://mafreebox.freebox.fr/api/v3/connection/'

    r = requests.get(api_url, headers=headers)

    if r.status_code == 200:
        return r.json()
    else:
        print 'Failed request: %s\n' % r.text



def get_ftth_status(headers):
    api_url = 'http://mafreebox.freebox.fr/api/v3/connection/ftth/'

    r = requests.get(api_url, headers=headers)

    if r.status_code == 200:
        return r.json()
    else:
        print 'Failed request: %s\n' % r.text


# Main
if __name__ == '__main__':

    freebox_app_id = "fr.freebox.seximonitor"
    freebox_app_token = "CHANGE_THIS"
    track_id = "CHANGE_THIS"

    # Fetch challenge
    resp = get_challenge(track_id)
    challenge = resp['result']['challenge']

    # Generate session password
    h = hmac.new(freebox_app_token, challenge, sha1)
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

    myData['bytes_down'] = jsonRaw['result']['bytes_down']
    myData['bytes_up'] = jsonRaw['result']['bytes_up']
    myData['rate_down'] = jsonRaw['result']['rate_down']
    myData['rate_up'] = jsonRaw['result']['rate_up']
    if jsonRaw['result']['state'] == "up":
        myData['state'] = 1
    else:
        myData['state'] = 0

    # Fetch ftth signal stats
    jsonRaw = get_ftth_status(headers)

    myData['sfp_pwr_rx'] = jsonRaw['result']['sfp_pwr_rx']
    myData['sfp_pwr_tx'] = jsonRaw['result']['sfp_pwr_tx']

    # Prepping Graphite Data format
    timestamp = int(time.time())

    # Output the information
    print "freebox.bytes_down %s %d" % (myData['bytes_down'], timestamp)
    print "freebox.bytes_up %s %d" % (myData['bytes_up'], timestamp)
    print "freebox.rate_down %s %d" % (myData['rate_down'], timestamp)
    print "freebox.rate_up %s %d" % (myData['rate_up'], timestamp)
    print "freebox.state %s %d" % (myData['state'], timestamp)
    print "freebox.sfp_pwr_rx %s %d" % (myData['sfp_pwr_rx'], timestamp)
    print "freebox.sfp_pwr_tx %s %d" % (myData['sfp_pwr_tx'], timestamp)
