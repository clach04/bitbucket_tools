# bitbucket-_tools

random tools for dealing with bitbucket.org repos

Getting my notes off my machine and in a shareable state.

## Tools

### bitbucket-cli - 2019

Updated version that works as of 2019, with REST v2.0 API https://developer.atlassian.com/bitbucket/api/2/reference/resource/

https://bitbucket.org/arrizza/bitbucket-cli/src/master/

Also includes a tool convert_to_git (recommend bitbucket-hg-to-git instead)

## bitbucket-hg-to-git

https://bitbucket.org/edrandall/bitbucket-hg-to-git

creates new BitBucket git repos from mercurial ones. Handles some meta data/tags.

### Migrating away from BitBucket

Lots of options, none complete.

GitHub's code/history import https://github.com/new/import worked well for me to import and convert a Mercurial code repo. It does not handle:
* project description - needs to manually copy/pasted 
* project logo/avatar/image  - needs to manually set (note you may not be able to get the original image that was used to upload, only a scaled-down copy unless you have the original stored somewhere)
* Issues / history / attachments
* PRs / history
* Downloads
* wiki

