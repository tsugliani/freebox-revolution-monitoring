#!/usr/bin/env python
# pylint: disable=C0103,C0111

import json
import requests

def get_authorization():
    api_url = 'http://mafreebox.freebox.fr/api/v3/login/authorize/'
    headers = {'Content-type': 'application/json'}
    app_info = {
        'app_id': 'fr.freebox.seximonitor',
        'app_name': 'SexiMonitor',
        'app_version': '0.4.2',
        'device_name': 'SexiServer'
    }
    json_payload = json.dumps(app_info)

    r = requests.post(api_url, headers=headers, data=json_payload)

    if r.status_code == 200:
        return r.json()
    else:
        print 'Failed registration: %s\n' % r.text

if __name__ == '__main__':
    resp = get_authorization()

    print '[Track ID] {}'.format(resp['result']['track_id'])
    print '[App token] {}'.format(resp['result']['app_token'])
    print 'Press on the right arrow on the Freebox Server and validate the app registration'
