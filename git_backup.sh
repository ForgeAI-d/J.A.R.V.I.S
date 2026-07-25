#!/bin/bash

cd /home/domenik/Projekte/J.A.R.V.I.S || exit

git add .

if git diff --cached --quiet; then
    echo "Keine Änderungen zum Hochladen."
    exit 0
fi

git commit -m "Auto backup $(date '+%Y-%m-%d %H:%M:%S')"
git push
