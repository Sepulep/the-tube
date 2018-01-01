#!/bin/bash
export PATH=":${PATH:-"/usr/bin:/bin:/usr/local/bin"}"
export LD_LIBRARY_PATH=":${LD_LIBRARY_PATH:-"/usr/lib:/lib"}"
export HOME="/mnt/utmp/thetube" XDG_CONFIG_HOME="/mnt/utmp/thetube"

export PATH=$PATH:/mnt/utmp/thetube/bin
export LD_LIBRARY_PATH=/mnt/utmp/thetube/lib:$LD_LIBRARY_PATH

export HOME="/mnt/utmp/thetube"

ldd /mnt/utmp/thetube/bin/mpv

#Automount of PanPlayer2

pnd_cb="panplayer2"
pnd_folder="panplayer2"
pnd_name="PanPlayer2"
if [ -e /mnt/utmp/$pnd_folder/bin/mplayer ];then
 panplayer2=1
 mounted="Found $pnd_name"
else
#check if it exist
tmp=( /usr/share/applications/${pnd_cb}*.desktop )
tmp="${tmp[0]}"
echo $tmp

if [ ! -e $tmp ];then
 #no panplayer2....
 mounted="$pnd_name not found"
else
#grab where is the pnd
pnd_path=$(sed -n 's/.*X-Pandora-Object-Path *= *\([^ ]*.*\)/\1/p' < $tmp )
pnd_name=$(sed -n 's/.*X-Pandora-Object-Filename *= *\([^ ]*.*\)/\1/p' < $tmp )
path_to_pnd="$pnd_path/$pnd_name"
 
#automount it
/usr/pandora/scripts/pnd_run.sh -p "$path_to_pnd" -b "$pnd_folder" -m
panplayer2=2
mounted="Mounted $pnd_name"
fi
fi

echo $mounted

OPTION1="run The Tube"
OPTION2a="run The Tube browser only"
OPTION2b="run The Tube clipboard player only"
OPTION3="update youtube-dl"
OPTION4="revert youtube-dl to pnd version"
OPTION5="enter new API key"
OPTION6="revert API key to pnd version"

SELECT=`zenity --list --width=360 --height=280 \
  --title="What do you want to run?" --radiolist \
  --column="" --column="Description" \
   TRUE "$OPTION1" \
   FALSE "$OPTION2a" \
   FALSE "$OPTION2b" \
   FALSE "$OPTION3" \
   FALSE "$OPTION4" \
   FALSE "$OPTION5" \
   FALSE "$OPTION6"`

if [[ $? -eq 1 ]]; then
exit 1
fi

echo $SELECT
if [ "$SELECT" == "$OPTION1" ]; then
cd /mnt/utmp/thetube/bin/
python driver.py -f -p -v mpv -d x11 -y pafy
fi
if [ "$SELECT" == "$OPTION2a" ]; then
cd /mnt/utmp/thetube/bin/
python thetube.py -f -p -v mpv -d x11 -y pafy
fi
if [ "$SELECT" == "$OPTION2b" ]; then
cd /mnt/utmp/thetube/bin/
zenity --info --text="The Tube clipboard player: plays youtube links copied to the clipboard (ctrl-c) automagically until 'stop' is copied to the clipboard" \
  --timeout=5 &
python clipplayer.py -f -p -v mpv -d x11 -y pafy
#~ zenity --info --text="The Tube clipboard player has shutdown"
fi
if [ "$SELECT" == "$OPTION3" ]; then
cd /mnt/utmp/thetube/bin/
if [ ! -f youtube-dl.orig ]; then
cp youtube-dl youtube-dl.orig
fi
./youtube-dl -U &> /tmp/youtube-dl_update
cat /tmp/youtube-dl_update | zenity --text-info --width=360 --height=240
fi
if [ "$SELECT" == "$OPTION4" ]; then
cd /mnt/utmp/thetube/bin/
if [ -f youtube-dl.orig ]; then
cp youtube-dl.orig youtube-dl
zenity --warning --text="Copied back pnd version."
else
zenity --warning --text="Old version not found."
exit 1
fi
fi
if [ "$SELECT" == "$OPTION5" ]; then
cd /mnt/utmp/thetube/bin/
zenity --entry --title="Enter new API key" \
--text="enter a new youtube v3 enabled API key:" > API_KEY
fi
if [ "$SELECT" == "$OPTION6" ]; then
cd /mnt/utmp/thetube/bin/
if [ -f API_KEY.org ]; then
cp API_KEY.org API_KEY
zenity --warning --text="Copied back pnd version."
else
zenity --warning --text="Old version not found."
exit 1
fi
fi

if [ "$panplayer2" == "2" ];then
 /usr/pandora/scripts/pnd_run.sh -p "$path_to_pnd" -b "$pnd_folder" -u
 sleep 1
fi

