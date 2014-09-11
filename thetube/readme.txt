The Tube

A freeware minimalistic youtube browser.

On start-up you can choose whether to start The Tube or to update 
the included youtube-dl should that become necessary. Also, an option 
to revert back youtube-dl is included. Note that by default, The Tube 
now uses the pafy library instead (but you can toggle with 'y').

You can use the mouse or the keyboard for input. Press h or the help 
button to get help on the keyboard shortcuts. Videos can be played from 
the browser by double clicking or pressing enter, or downloaded by 
pressing <d>. Currently it no longer needs mplayer installed: 'm' 
toggles between different playback options (mpv or mplayer). In any 
case, should it become necessary, it can be installed with the community 
codec pack: http://openpandora.org/downloads/CodecPack.pnd).

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
pafy: https://github.com/np1/pafy
