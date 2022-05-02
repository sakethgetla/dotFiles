#!/bin/bash

i3-msg "workspace 1; append_layout /home/dawes/.i3/workspace-1.json"
i3-msg "workspace 1; exec emacs"
i3-msg "workspace 1; exec qutebrowser"
i3-msg "workspace 1; exec xterm"

#setxkbmap -option caps:swapescape
#xmodmap ~/.xmodmap
