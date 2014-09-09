The Tube

A freeware minimalistic youtube browser based on youtube-dl and mpv.

On start-up you can choose whether you want playback for tv-out 
(Currently playback for TV-out is done with the x11 driver, so main 
layer should be selected in the TV-out configuration). There is alo an 
option to update the included youtube-dl should that become necessary. 
Also, an option to revert back youtube-dl is included.

You can use the mouse or the keyboard for input. Press h or the help 
button to get help on the keyboard shortcuts. Videos can be played from 
the browser by double clicking or pressing enter, or downloaded by 
pressing <d>. Currently it no longer needs mplayer installed. (In any 
case, should it become necessary, it can be done with the community 
codec pack: http://openpandora.org/downloads/CodecPack.pnd )

The preferred quality of playback can be selected - it will fallback on 
lower bitrates if the preferred option is not available.

A rudimentary playlist is implemented: <a> to add a video to the 
playlist, <l> to toggle the playlist view, <r> to remove - if you are in 
playlist view you can insert a video you just removed by pressing <a>. 
<c> clears the list. <space> plays the playlist.

youtube-dl: rg3.github.io/youtube-dl/
mplayer: www.mplayerhq.hu/
mpv: mpv.io
An optimized yuv converter from the Mozilla is included (mozilla.org)
