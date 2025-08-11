#!/bin/zsh

config=$1

case $config in 
  laptop | l)
    print 'laptop config'
    ;;
  moniter | m)
    print 'moniter config'
    ;;
  *)
    print 'invalid input, enter one of [laptop, l, moniter, m]'
    print 'eg.'
    print '   ./file.zsh laptop'
    ;;
esac
