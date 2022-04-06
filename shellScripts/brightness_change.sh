#!/bin/bash

if [ "$1" != "" ]; then
    if [ "$1" == "+" ]; then
        sudo brightnessctl --exponent=2 set 3%+
    fi
    if [ "$1" == "-" ]; then
        sudo brightnessctl --exponent=2 set 3%-
    fi
else
    echo "error!!"
    echo "usage sh [filename] [brightness range = 0-1]"
fi
