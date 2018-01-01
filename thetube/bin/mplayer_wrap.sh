#!/bin/bash

# wraps mplayer at /mnt/utmp/panplayer2/

export LD_LIBRARY_PATH=/mnt/utmp/panplayer2/lib:${LD_LIBRARY_PATH}
export SDL_VIDEODRIVER=omapdss

/mnt/utmp/panplayer2/bin/mplayer $0
