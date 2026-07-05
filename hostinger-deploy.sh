#!/bin/sh
set -e

USER=u116515650
HOST=195.35.39.200
DIR=/domains/natebent.com/public_html/
PORT=65002

if [ "$1" = "--untrack-public" ]; then
    echo "==> Untracking public/ from git (one-time cleanup)"
    git rm -r --cached public/
    echo "Done. Review the changes, then commit them:"
    echo "  git commit -m 'Untrack public/ build output'"
    echo "  git push"
    exit 0
fi

echo "==> Building site"
hugo

echo "==> Deploying to ${HOST}"
rsync -avz -e "ssh -p ${PORT}" --delete public/ "${USER}@${HOST}:~${DIR}"

echo "==> Committing source changes"
git add .
if git diff --cached --quiet; then
    echo "No changes to commit"
else
    git commit -m "hugo deploy $(date +%Y-%m-%d_%H:%M)"
    git push
fi

echo "==> Done"
exit 0
