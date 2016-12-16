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


def get_xdsl_status(headers):
    api_url = '%s/connection/xdsl/' % ENDPOINT

    r = requests.get(api_url, headers=headers)

    if r.status_code == 200:
        return r.json()
    else:
        print('Failed request: %s\n' % r.text)


def get_system_config(headers):
    api_url = '%s/system/' % ENDPOINT

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
    myData['bytes_down'] = jsonRaw['result']['bytes_down']  # total in bytes since last connection
    myData['bytes_up'] = jsonRaw['result']['bytes_up']

    myData['rate_down'] = jsonRaw['result']['rate_down']  # current rate in byte/s
    myData['rate_up'] = jsonRaw['result']['rate_up']

    myData['bandwidth_down'] = jsonRaw['result']['bandwidth_down']  # available bw in bit/s
    myData['bandwidth_up'] = jsonRaw['result']['bandwidth_up']

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

        myData['sfp_pwr_rx'] = jsonRaw['result']['sfp_pwr_rx']  # scaled by 100 (in dBm)
        myData['sfp_pwr_tx'] = jsonRaw['result']['sfp_pwr_tx']

    ###
    # xDSL specific
    if connection_media == "xdsl":
        jsonRaw = get_xdsl_status(headers)

        myData['xdsl_uptime'] = jsonRaw['result']['status']['uptime']  # in seconds
        
        myData['xdsl_down_es'] = jsonRaw['result']['down']['es']  # increment
        myData['xdsl_down_attn'] = jsonRaw['result']['down']['attn']  # in dB
        myData['xdsl_down_snr'] = jsonRaw['result']['down']['snr']  # in dB
        myData['xdsl_down_rate'] = jsonRaw['result']['down']['rate']  # ATM rate in kbit/s
        myData['xdsl_down_hec'] = jsonRaw['result']['down']['hec']  # increment
        myData['xdsl_down_crc'] = jsonRaw['result']['down']['crc']  # increment
        myData['xdsl_down_ses'] = jsonRaw['result']['down']['ses']  # increment
        myData['xdsl_down_fec'] = jsonRaw['result']['down']['fec']  # increment
        myData['xdsl_down_maxrate'] = jsonRaw['result']['down']['maxrate']  # ATM max rate in kbit/s
        myData['xdsl_down_rtx_tx'] = jsonRaw['result']['down']['rtx_tx']  # G.INP on/off
        myData['xdsl_down_rtx_c'] = jsonRaw['result']['down']['rtx_c']  # G.INP corrected
        myData['xdsl_down_rtx_uc'] = jsonRaw['result']['down']['rtx_uc']  # G.INP uncorrected

        myData['xdsl_up_es'] = jsonRaw['result']['up']['es']
        myData['xdsl_up_attn'] = jsonRaw['result']['up']['attn']
        myData['xdsl_up_snr'] = jsonRaw['result']['up']['snr']
        myData['xdsl_up_rate'] = jsonRaw['result']['up']['rate']
        myData['xdsl_up_hec'] = jsonRaw['result']['up']['hec']
        myData['xdsl_up_crc'] = jsonRaw['result']['up']['crc']
        myData['xdsl_up_ses'] = jsonRaw['result']['up']['ses']
        myData['xdsl_up_fec'] = jsonRaw['result']['up']['fec']
        myData['xdsl_up_maxrate'] = jsonRaw['result']['up']['maxrate']
        myData['xdsl_up_rtx_tx'] = jsonRaw['result']['up']['rtx_tx']  # G.INP on/off
        myData['xdsl_up_rtx_c'] = jsonRaw['result']['up']['rtx_c']  # G.INP corrected
        myData['xdsl_up_rtx_uc'] = jsonRaw['result']['up']['rtx_uc']  # G.INP uncorrected


    ##
    # General infos
    sysJsonRaw = get_system_config(headers)
    myData['sys_fan_rpm'] = sysJsonRaw['result']['fan_rpm']  # rpm
    myData['sys_temp_sw'] = sysJsonRaw['result']['temp_sw']  # Temp Switch, degree Celcius
    myData['sys_uptime'] = sysJsonRaw['result']['uptime_val']  # Uptime, in seconds
    myData['sys_temp_cpub'] = sysJsonRaw['result']['temp_cpub']  # Temp CPU Broadcom, degree Celcius
    myData['sys_temp_cpum'] = sysJsonRaw['result']['temp_cpum']  # Temp CPU Marvell, degree Celcius

    # Prepping Graphite Data format
    timestamp = int(time.time())

    # Output the information
    for i in myData:
        print("freebox.%s %s %d" % (i, myData[i], timestamp))


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