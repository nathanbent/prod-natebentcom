#!/bin/sh
USER=u116515650
HOST=195.35.39.200
DIR=/domains/natebent.com/public_html/   # the directory where your web site files should go
PORT=65002

hugo && rsync -avz -e 'ssh -p 65002' --delete public/ ${USER}@${HOST}:~/${DIR} # this will delete everything on the server that's not in the local public folder

exit 0
