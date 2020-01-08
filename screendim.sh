#!/bin/bash
# Bash script to control the monitor brightness

#echo "Positional Parameters"
#echo '$0 = ' $0
#echo '$1 = ' $1
#echo '$2 = ' $2
#echo '$3 = ' $3
if [ "$1" != "" ]; then
    xrandr --output eDP-1 --brightness $1
else
    echo "error!!"
    echo "usage sh [filename] [brightness range = 0-1]"
fi
