#!/bin/sh

# wraps mplayer at /mnt/utmp/panplayer2/

export LD_LIBRARY_PATH=/mnt/utmp/panplayer2/lib:${LD_LIBRARY_PATH}
export SDL_VIDEODRIVER=omapdss

#~ echo ldd:
#~ ldd /mnt/utmp/panplayer2/bin/mplayer

echo wrapper call arg:
echo $@

/mnt/utmp/panplayer2/bin/mplayer $@
