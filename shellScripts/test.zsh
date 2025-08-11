#!/bin/zsh

# laptop, l, moniter, m
config=$1

case $config in 
  laptop | l)
    print 'laptop config'
    setxkbmap -layout us -variant colemak_dh_iso
    
    setxkbmap -option caps:swapescape
    setxkbmap -option ctrl:swap_lalt_lctl
    
    xrandr --output eDP --auto --primary
    xrandr --output DisplayPort-8 --off
    xrandr --output DisplayPort-9 --off
    ;;
  moniter | m)
    print 'moniter config'
    setxkbmap -layout us 
    setxkbmap -option
    
    xrandr --output DisplayPort-8 --auto --primary
    xrandr --output eDP --off
    ;;
  *)
    print 'invalid input, enter one of [laptop, l, moniter, m']
    print 'eg.'
    print '   ./file.zsh laptop'
    ;;
esac
