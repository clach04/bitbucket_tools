#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
# export Mercurial (and git) projects on bitbucket.org to local disk
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

log = logging.getLogger(__name__)
logging.basicConfig()  # TODO include function name/line numbers in log
if os.environ.get('BB_DUMP_DEBUG'):
    if os.environ.get('BB_DUMP_DEBUG').lower() == 'info':
        log.setLevel(level=logging.INFO)
    else:
        log.setLevel(level=logging.DEBUG)
log.setLevel(level=logging.INFO)


def safe_mkdir(newdir):
    result_dir = os.path.abspath(newdir)
    try:
        os.makedirs(result_dir)
    except OSError as info:
        if info.errno == 17 and os.path.isdir(result_dir):
            pass
        else:
            raise


def get_url(url, headers=None):
    log.debug('get_url=%r', url)
    response = None
    try:
        if headers:
            request = Request(url, headers=headers)
        else:
            request = Request(url)  # may not be needed
        response = urlopen(request)
        url = response.geturl()  # may have changed in case of redirect
        code = response.getcode()
        result = response.read()
        return result
    finally:
        if response != None:
            response.close()

def get_url_json(url, headers=None):
    content = get_url(url, headers=headers)
    content = content.decode("utf-8")  # Pre Python 3.6 hack (Raspberry Pi in 2019 still uses older release)
    return json.loads(content)


def get_list(url, headers=None):
    x = get_url_json(url, headers=headers)
    values = x['values']
    next = x.get('next')
    log.debug('len(values)=%d', len(values))
    while next:
        x = get_url_json(next, headers=headers)
        next = x.get('next')
        values += x['values']
        log.debug('len(values)=%d', len(values))
    return values


def gen_local_project_dir_name(project_metadata):
    if project_metadata['is_private']:
        dir_name_list = ['private']
    else:
        dir_name_list = ['public']
    dir_name_list.append(project_metadata['slug'])
    dir_name = os.path.join(*dir_name_list)
    return dir_name


class EasyBitBucketAPI():
    def __init__(self, username, password=None, project_owner=None):
        assert username is not None, 'need a username, set OS variable BB_USERNAME'
        project_owner = project_owner or username
        self.repo_info = {'username': username, 'secret': password, 'project_owner': project_owner}
        if password:
            log.warning('password being used, any git repos will contain password in config checkout file!')
            encoded_auth = base64.b64encode("{username}:{secret}".format(**self.repo_info).encode()).decode()
            self.headers = dict([("Authorization", "Basic {}".format(encoded_auth))])
        else:
            self.headers = None

    def dump_project_list(self):
        # dump meta data lists of all projects
        url = 'https://api.bitbucket.org/2.0/repositories/{project_owner}'.format(**self.repo_info)
        result = get_list(url, headers=self.headers)
        return result

    def dump_project_metadata(self, project_name):
        # dump meta data detail for each project
        # project description
        # logo
        tmp_repo_info = {'project_name': project_name}
        tmp_repo_info.update(self.repo_info)
        url = 'https://api.bitbucket.org/2.0/repositories/{project_owner}/{project_name}'.format(**tmp_repo_info)
        result = get_url_json(url, headers=self.headers)
        return result

    def dump_project_issues(self, project_slug):
        tmp_repo_info = {'project_slug': project_slug}
        tmp_repo_info.update(self.repo_info)
        url = 'https://api.bitbucket.org/2.0/repositories/{project_owner}/{project_slug}/issues'.format(**tmp_repo_info)
        try:
            result = get_list(url, headers=self.headers)
        except HTTPError as error:
            if error.code == 404:
                log.warning('DEBUG dump_project_issues() assuming no issues for export - got 404 for %r', url)
                # FIXME
                # either a bad URL or could be correct but there are no issues - not sure how to tell here.
                return []  # always assume no issues
            log.error('dump_project_issues http error %r', error.errno)
            raise
        return result

    def dump_project_downloads(self, project_slug):
        # dump meta data and the files
        tmp_repo_info = {'project_slug': project_slug}
        tmp_repo_info.update(self.repo_info)
        url = 'https://api.bitbucket.org/2.0/repositories/{project_owner}/{project_slug}/downloads'.format(**tmp_repo_info)
        log.debug('dump_project_downloads()  %r', url)
        result = get_list(url, headers=self.headers)
        return result

    def dump_project_code(self, project_slug, dest_path, scm_type):
        # source checkout
        # could use URL in meta data but password has to be specificed somewhere...
        tmp_repo_info = {'project_slug': project_slug, 'dest_path': dest_path}
        tmp_repo_info.update(self.repo_info)
        if scm_type == 'hg':
            cmd = 'hg clone https://{username}:{secret}@bitbucket.org/{project_owner}/{project_slug} {dest_path}'.format(**tmp_repo_info)
        elif scm_type == 'git':
            cmd = 'git clone --mirror https://{username}:{secret}@bitbucket.org/{project_owner}/{project_slug} {dest_path}'.format(**tmp_repo_info)
            cmd = 'git clone https://{username}:{secret}@bitbucket.org/{project_owner}/{project_slug} {dest_path}'.format(**tmp_repo_info)
        else:
            raise NotImplemented('unknown scm type %r' % scm_type)
        log.debug('CMD: %r', cmd)
        log.debug('CMD: %s', cmd)
        subprocess.check_call(cmd)

    def dump_project_wiki(self, project_slug, dest_path, scm_type):
        # wiki source checkout
        tmp_repo_info = {'project_slug': project_slug, 'dest_path': dest_path}
        tmp_repo_info.update(self.repo_info)
        if scm_type == 'hg':
            cmd = 'hg clone https://{username}:{secret}@bitbucket.org/{project_owner}/{project_slug}/wiki {dest_path}'.format(**tmp_repo_info)
        elif scm_type == 'git':
            cmd = 'git clone --mirror https://{username}:{secret}@bitbucket.org/{project_owner}/{project_slug}/wiki {dest_path}'.format(**tmp_repo_info)
            cmd = 'git clone https://{username}:{secret}@bitbucket.org/{project_owner}/{project_slug}/wiki {dest_path}'.format(**tmp_repo_info)
        else:
            raise NotImplemented('unknown scm type %r' % scm_type)
        log.debug('CMD: %s', cmd)
        subprocess.check_call(cmd)

    def dump_one_project(self, project_slug):
        # export everything to file system for one project
        log.info('dump_one_project() project_slug %r', project_slug)

        project_metadata = self.dump_project_metadata(project_slug)
        log.debug('dump_project_metadata() result=%r', project_metadata)
        #log.debug('%s', json.dumps(project_metadata, indent=4))
        # NOTE `project_metadata` probably patches `project`
        # safe_mkdir()
        log.debug('\thas_wiki %r', project_metadata['has_wiki'])
        log.debug('\tavatar %r', project_metadata['links']['avatar'])
        log.debug('\tis_private %r', project_metadata['is_private'])
        dir_name = gen_local_project_dir_name(project_metadata)
        safe_mkdir(dir_name)
        image_filename = dir_name +'.png'  # assume png
        #image = get_url(project_metadata['links']['avatar']['href'], headers=self.headers)
        image = get_url(project_metadata['links']['avatar']['href'])
        f = open(image_filename, 'wb')
        f.write(image)
        f.close()

        issues_filename = os.path.join(dir_name, 'issues.json')
        project_issues = self.dump_project_issues(project_slug)
        #project_issues = {'issues': project_issues}
        log.debug('project_issues=%r', project_issues)
        if project_issues:
            f = open(issues_filename, 'wb')
            json.dump(project_issues, f)
            f.close()

        project_downloads = self.dump_project_downloads(project_slug)
        log.debug('project_downloads=%r', project_downloads)
        if project_downloads:
            downloads_dirname = os.path.join(dir_name, 'downloads')
            safe_mkdir(downloads_dirname)
            downloads_filename = os.path.join(dir_name, 'downloads.json')
            f = open(downloads_filename, 'wb')
            json.dump(project_downloads, f)
            f.close()
            for download in project_downloads:
                log.debug('download %r', download)
                download_name = os.path.join(downloads_dirname, download['name'])
                url = download['links']['self']['href']
                data = get_url(url)
                f = open(download_name, 'wb')
                f.write(data)
                f.close()

        code_dirname = os.path.join(dir_name, 'code')
        result = self.dump_project_code(project_slug, code_dirname, project_metadata['scm'])
        log.debug('result=%r', result)

        if project_metadata.get('has_wiki'):
            wiki_dirname = os.path.join(dir_name, 'wiki')
            result = self.dump_project_wiki(project_slug, wiki_dirname, project_metadata['scm'])
            log.debug('result=%r', result)
        log.info('dump_one_project() complete for  %r', project_slug)


def doit():
    username = os.environ.get('BB_USERNAME')
    password = os.environ.get('BB_PASSWORD')
    r = EasyBitBucketAPI(username, password)

    all_repo_meta_filename = 'all_repos.json'
    if not os.path.exists(all_repo_meta_filename):
        project_list = r.dump_project_list()
        #log.debug('project_list=%r', project_list)
        tmp_str = json.dumps(project_list,indent=4)
        f = open(all_repo_meta_filename, 'wb')
        f.write(tmp_str)
        f.close()
    else:
        log.info('using cached project_list from file %r', all_repo_meta_filename)
        f = open(all_repo_meta_filename, 'rb')
        project_list = json.load(f)
        f.close()

    for project in project_list:
        project_name = project['name']
        project_slug = project['slug']
        log.info('project_name %r', project_name)
        r.dump_one_project(project_slug)
    log.warning('any git repos will contain password in config checkout file!')


def main(argv=None):
    if argv is None:
        argv = sys.argv

    print('Python %s on %s' % (sys.version, sys.platform))

    doit()

    return 0


if __name__ == "__main__":
    sys.exit(main())
