The Tube

A freeware minimalistic youtube browser.

On start-up you can choose whether to start The Tube or to update 
the included youtube-dl should that become necessary. Also, an option 
to revert back youtube-dl is included. Note that by default, The Tube 
now uses the pafy library instead (but you can toggle with 'y').

There is also an option to change the API key (can be obtained from 
google, generate one with the youtube v3 API enabled), or revert back
to the key included in the pnd.

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

The mpv player is included. It has been patched to use the neon optimized 
yuv to rgb565 converter from mozilla firefox (mozilla.org) in case the 
x11 driver is used. This is the default and recommended, even if it may
benefit from a little overclocking on CC and Rebirth pandoras as it 
allows for seamless playlist play and tv-out (use main layer)..

youtube-dl: rg3.github.io/youtube-dl/
mplayer: www.mplayerhq.hu/
mpv: mpv.io
pafy: https://github.com/np1/pafy
