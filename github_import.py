#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
# import Git (and maybe Mercurial) projects from (dump_repos.py) local disk into GitHub
# Python 3 or Python 2
# Attempts to dump meta data
# pretty much hard coded to username and password - doesn't attempt to use keys or handle 2fa

import logging
import os
import os.path
import subprocess
import sys
import base64
import json
import sys
try:
    # Assume Python 3.x
    from urllib.error import URLError, HTTPError
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
except ImportError:
    # Probably Python2
    from urllib import urlencode
    from urllib2 import Request, urlopen
    from urllib2 import URLError, HTTPError

try:
    from getpass import getpass
except ImportError:
    def getpass(prompt_str):
        return raw_input( prompt_str + 'WARNING will echo! ' )

import dump_repos


log = logging.getLogger(__name__)
logging.basicConfig()  # TODO include function name/line numbers in log
if os.environ.get('BB_DUMP_DEBUG'):
    if os.environ.get('BB_DUMP_DEBUG').lower() == 'info':
        log.setLevel(level=logging.INFO)
    else:
        log.setLevel(level=logging.DEBUG)
log.setLevel(level=logging.INFO)



def post_url_json(url, dict_payload=None, headers=None):
    headers = headers or {'content-type': 'application/json'}  # optionally set headers
    data = json.dumps(dict_payload).encode('utf-8')
    log.info('url: %r' % url)
    log.info('json request: %r' % data)

    req = Request(url, data, headers)
    f = urlopen(req)
    response_str = f.read()  # read entire response, could use json.load()
    f.close()

    log.info('response_str: %r' % response_str)
    response = json.loads(response_str)
    return response


class EasyGitHubAPI():
    def __init__(self, username, password=None):
        assert username is not None, 'need a username, set OS variable GH_USERNAME'
        self.repo_info = {'username': username, 'secret': password}
        if password:
            encoded_auth = base64.b64encode("{username}:{secret}".format(**self.repo_info).encode()).decode()
            self.headers = dict([("Authorization", "Basic {}".format(encoded_auth))])
        else:
            self.headers = None

    def create_repo(self, name, private=False, has_wiki=False, has_issues=False, description=None, homepage=None):
        # https://developer.github.com/v3/repos/#create-a-repository-for-the-authenticated-user
        url = 'https://api.github.com/user/repos'
        dict_payload = {
            'name': name,
            'private': private,
            'has_wiki': has_wiki,
            'has_issues': has_issues,
            'description': description.replace('\r', ' ').replace('\n', ' '),  # Bitbucket supported newlines (and possibly longer descriptions?)
            'homepage': homepage
            }
        #import pdb ; pdb.set_trace()
        return post_url_json(url, dict_payload, headers=self.headers)


def doit():
    username = os.environ.get('GH_USERNAME') or os.environ.get('USERNAME') or os.environ.get('USER')
    password_prompt = 'GitHub password for user %s: ' % username
    password = os.environ.get('GH_PASSWORD') or getpass(password_prompt)
    r = EasyGitHubAPI(username, password)

    all_repo_meta_filename = 'all_repos.json'
    log.info('using cached project_list from file %r', all_repo_meta_filename)
    f = open(all_repo_meta_filename, 'rb')
    project_list = json.load(f)
    f.close()

    project_name_search = 'vorton'  # DEBUG
    found_project = None
    for project in project_list:
        project_name = project['name']
        if project_name == project_name_search:
            found_project = project
        project_slug = project['slug']
        log.info('%s (%s) project_name %r', 'private' if project['is_private'] else 'public', project['scm'], project_name)

    # TODO Create repo (with all text meta data)
    # TODO push --mirror repo
    # TODO upload additional meta data, e.g. logo
    # TODO Create wiki repo
    # TODO push wiki
    # TODO upload downloads
    # TODO upload/import issues
    """
    project = found_project
    new_repo_name = project['name']
    new_repo_name = 'test_curl'  # DEBUG
    #project['description'] = 'test curl description'  # DEBUG WORKS
    #project['description'] = 'x' * 201  # DEBUG WORKS

    dir_name = dump_repos.gen_local_project_dir_name(project)
    code_dirname = os.path.join(dir_name, 'code')
    print(repr(code_dirname))

    result = r.create_repo(new_repo_name, private=project['is_private'], has_wiki=project['has_wiki'], has_issues=project['has_issues'], description=project['description'], homepage=project['website'])
    print(result)
    """


def main(argv=None):
    if argv is None:
        argv = sys.argv

    print('Python %s on %s' % (sys.version, sys.platform))

    doit()

    return 0


if __name__ == "__main__":
    sys.exit(main())
