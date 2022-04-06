#!/bin/bash

# making it easy to push code
git add .

if [ "$1" != "" ]; then
    git commit -m "$1"
else
    git commit -m "autopushed"
fi
git push
