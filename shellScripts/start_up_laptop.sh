#!/bin/bash

# laptop screen config

setxkbmap -layout us -variant colemak_dh_iso

setxkbmap -option caps:swapescape
setxkbmap -option ctrl:swap_lalt_lctl

xrandr --output eDP --auto --primary
xrandr --output DisplayPort-8 --off
xrandr --output DisplayPort-9 --off
