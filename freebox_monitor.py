#!/usr/bin/env python
# pylint: disable=C0103,C0111,W0621
from __future__ import print_function

import requests
import os
import json
import hmac
import time
import argparse
import sys
from hashlib import sha1

if sys.version_info >= (3, 0):
    import configparser as configp
else:
    import ConfigParser as configp

#
# Freebox API SDK / Docs: http://dev.freebox.fr/sdk/os/login/
#

VERSION = "0.4.4"


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


def get_internal_disk_stats(headers):
    api_url = '%s/storage/disk/1' % ENDPOINT

    r = requests.get(api_url, headers=headers)

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


def get_switch_status(headers):
    api_url = '%s/switch/status/' % ENDPOINT

    r = requests.get(api_url, headers=headers)

    if r.status_code == 200:
        return r.json()
    else:
        print('Failed request: %s\n' % r.text)


def get_switch_port_stats(headers, port):
    api_url = '%s/switch/port/%s/stats' % (ENDPOINT, port)

    r = requests.get(api_url, headers=headers)

    if r.status_code == 200:
        return r.json()
    else:
        print('Failed request: %s\n' % r.text)


def get_and_print_metrics(creds, s_switch, s_ports, s_sys):
    freebox_app_id = "fr.freebox.seximonitor"

    # Fetch challenge
    resp = get_challenge(creds['track_id'])
    challenge = resp['result']['challenge']

    # Generate session password
    if sys.version_info >= (3, 0):
        h = hmac.new(bytearray(creds['app_token'], 'ASCII'), bytearray(challenge, 'ASCII'), sha1)
    else:
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
    my_data = {}

    # Fetch internal disk stats
    json_raw=get_internal_disk_stats(headers)
    my_data['disk_total_bytes'] =  json_raw['result']['partitions'][0]['total_bytes']
    my_data['disk_used_bytes'] =  json_raw['result']['partitions'][0]['used_bytes']

    # Fetch connection stats
    json_raw = get_connection_stats(headers)

    # Generic datas, same for FFTH or xDSL
    my_data['bytes_down'] = json_raw['result']['bytes_down']  # total in bytes since last connection
    my_data['bytes_up'] = json_raw['result']['bytes_up']

    my_data['rate_down'] = json_raw['result']['rate_down']  # current rate in byte/s
    my_data['rate_up'] = json_raw['result']['rate_up']

    my_data['bandwidth_down'] = json_raw['result']['bandwidth_down']  # available bw in bit/s
    my_data['bandwidth_up'] = json_raw['result']['bandwidth_up']

    if json_raw['result']['state'] == "up":
        my_data['state'] = 1
    else:
        my_data['state'] = 0

    # ffth for FFTH (default)
    # xdsl for xDSL
    connection_media = json_raw['result']['media']

    ###
    # FFTH specific
    if connection_media == "ffth":
        json_raw = get_ftth_status(headers)

        my_data['sfp_pwr_rx'] = json_raw['result']['sfp_pwr_rx']  # scaled by 100 (in dBm)
        my_data['sfp_pwr_tx'] = json_raw['result']['sfp_pwr_tx']

    ###
    # xDSL specific
    if connection_media == "xdsl":
        json_raw = get_xdsl_status(headers)

        my_data['xdsl_uptime'] = json_raw['result']['status']['uptime']  # in seconds

        if json_raw['result']['status']['status'] == "down":  # unsynchronized
            my_data['xdsl_status'] = 0
        elif json_raw['result']['status']['status'] == "training":  # synchronizing step 1/4
            my_data['xdsl_status'] = 1
        elif json_raw['result']['status']['status'] == "started":  # synchronizing step 2/4
            my_data['xdsl_status'] = 2
        elif json_raw['result']['status']['status'] == "chan_analysis":  # synchronizing step 3/4
            my_data['xdsl_status'] = 3
        elif json_raw['result']['status']['status'] == "msg_exchange":  # synchronizing step 4/4
            my_data['xdsl_status'] = 4
        elif json_raw['result']['status']['status'] == "showtime":  # ready
            my_data['xdsl_status'] = 5
        elif json_raw['result']['status']['status'] == "disabled":  # disabled
            my_data['xdsl_status'] = 6
        else:  # unknown
            my_data['xdsl_status'] = 999

        my_data['xdsl_down_es'] = json_raw['result']['down']['es']  # increment
        my_data['xdsl_down_attn'] = json_raw['result']['down']['attn']  # in dB
        my_data['xdsl_down_snr'] = json_raw['result']['down']['snr']  # in dB
        my_data['xdsl_down_rate'] = json_raw['result']['down']['rate']  # ATM rate in kbit/s
        my_data['xdsl_down_hec'] = json_raw['result']['down']['hec']  # increment
        my_data['xdsl_down_crc'] = json_raw['result']['down']['crc']  # increment
        my_data['xdsl_down_ses'] = json_raw['result']['down']['ses']  # increment
        my_data['xdsl_down_fec'] = json_raw['result']['down']['fec']  # increment
        my_data['xdsl_down_maxrate'] = json_raw['result']['down']['maxrate']  # ATM max rate in kbit/s
        my_data['xdsl_down_rtx_tx'] = json_raw['result']['down']['rtx_tx']  # G.INP on/off
        my_data['xdsl_down_rtx_c'] = json_raw['result']['down']['rtx_c']  # G.INP corrected
        my_data['xdsl_down_rtx_uc'] = json_raw['result']['down']['rtx_uc']  # G.INP uncorrected

        my_data['xdsl_up_es'] = json_raw['result']['up']['es']
        my_data['xdsl_up_attn'] = json_raw['result']['up']['attn']
        my_data['xdsl_up_snr'] = json_raw['result']['up']['snr']
        my_data['xdsl_up_rate'] = json_raw['result']['up']['rate']
        my_data['xdsl_up_hec'] = json_raw['result']['up']['hec']
        my_data['xdsl_up_crc'] = json_raw['result']['up']['crc']
        my_data['xdsl_up_ses'] = json_raw['result']['up']['ses']
        my_data['xdsl_up_fec'] = json_raw['result']['up']['fec']
        my_data['xdsl_up_maxrate'] = json_raw['result']['up']['maxrate']
        my_data['xdsl_up_rtx_tx'] = json_raw['result']['up']['rtx_tx']  # G.INP on/off
        my_data['xdsl_up_rtx_c'] = json_raw['result']['up']['rtx_c']  # G.INP corrected
        my_data['xdsl_up_rtx_uc'] = json_raw['result']['up']['rtx_uc']  # G.INP uncorrected

    ##
    # General infos
    if s_sys:
        sys_json_raw = get_system_config(headers)
        my_data['sys_fan_rpm'] = sys_json_raw['result']['fan_rpm']  # rpm
        my_data['sys_temp_sw'] = sys_json_raw['result']['temp_sw']  # Temp Switch, degree Celcius
        my_data['sys_uptime'] = sys_json_raw['result']['uptime_val']  # Uptime, in seconds
        my_data['sys_temp_cpub'] = sys_json_raw['result']['temp_cpub']  # Temp CPU Broadcom, degree Celcius
        my_data['sys_temp_cpum'] = sys_json_raw['result']['temp_cpum']  # Temp CPU Marvell, degree Celcius

    ##
    # Switch status
    if s_switch:
        switch_json_raw = get_switch_status(headers)
        for i in switch_json_raw['result']:
            # 0 down, 1 up
            my_data['switch_%s_link' % i['id']] = 0 if i['link'] == "down" else 1
            # 0 auto, 1 10Base-T, 2 100Base-T, 3 1000Base-T
            # In fact the duplex is appended like 10BaseT-HD, 1000BaseT-FD, 1000BaseT-FD
            # So juse is an "in" because duplex isn't really usefull
            if "10BaseT" in i['mode']:
                my_data['switch_%s_mode' % i['id']] = 1
            elif "100BaseT" in i['mode']:
                my_data['switch_%s_mode' % i['id']] = 2
            elif "1000BaseT" in i['mode']:
                my_data['switch_%s_mode' % i['id']] = 3
            else:
                my_data['switch_%s_mode' % i['id']] = 0  # auto

    ##
    # Switch ports status
    if s_ports:
        for i in [1, 2, 3, 4]:
            switch_port_stats = get_switch_port_stats(headers, i)
            my_data['switch_%s_rx_bytes_rate' % i] = switch_port_stats['result']['rx_bytes_rate']  # bytes/s (?)
            my_data['switch_%s_tx_bytes_rate' % i] = switch_port_stats['result']['tx_bytes_rate']

    # Prepping Graphite Data format
    timestamp = int(time.time())

    # Output the information
    for i in my_data:
        print("freebox.%s %s %d" % (i, my_data[i], timestamp))


def get_auth():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    cfg_file = os.path.join(script_dir, ".credentials")

    f = configp.RawConfigParser()
    f.read(cfg_file)

    try:
        _ = f.get(args.Endpoint, "track_id")
        _ = f.get(args.Endpoint, "app_token")
    except configp.NoSectionError:
        print("Config is not registered, auth not done.")
	if args.register:
             return None
	else:
	     exit();

    return {'track_id': f.get(args.Endpoint, 'track_id'),
            'app_token': f.get(args.Endpoint, 'app_token')}


def write_auth(auth_infos):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    cfg_file = os.path.join(script_dir, ".credentials")
    f = configp.RawConfigParser()
    f.add_section(args.Endpoint)
    f.set(args.Endpoint, "track_id", auth_infos['track_id'])
    f.set(args.Endpoint, "app_token", auth_infos["app_token"])
    with open(cfg_file, "ab") as authFile:
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

    parser.add_argument('-e', '--endpoint',
                        dest='Endpoint',
			metavar='endpoint',
			default='mafreebox.freebox.fr',
                        help="Specify endpoint name or address")

    parser.add_argument('-S', '--status-switch',
                        dest='status_switch',
                        action='store_true',
                        help="Get and show switch status")

    parser.add_argument('-P', '--status-ports',
                        dest='status_ports',
                        action='store_true',
                        help="Get and show switch ports stats")

    parser.add_argument('-H', '--status-sys',
                        dest='status_sys',
                        action='store_true',
                        help="Get and show system status")
    args = parser.parse_args()


    ENDPOINT="http://"+args.Endpoint+"/api/v3/"

    auth = get_auth()

    if args.register:
        do_register(auth)
    elif args.status:
        register_status(auth)
    else:
        get_and_print_metrics(auth, args.status_switch, args.status_ports, args.status_sys)
