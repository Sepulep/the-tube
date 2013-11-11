#!/bin/sh
export PATH=":${PATH:-"/usr/bin:/bin:/usr/local/bin"}"
export LD_LIBRARY_PATH=":${LD_LIBRARY_PATH:-"/usr/lib:/lib"}"
export HOME="/mnt/utmp/thetube" XDG_CONFIG_HOME="/mnt/utmp/thetube"

export PATH=$PATH:/mnt/utmp/thetube/bin

export HOME="/mnt/utmp/thetube"

which mplayer
if [ $? -ne 0 ]; then
zenity --warning --text="mplayer not found - install the community codec pack"
exit 1
fi

OPTION1="run The Tube"
OPTION2="run The Tube for tv-out (set HW layer)"
OPTION3="update youtube-dl"

SELECT=`zenity --list --width=400 --height=300 \
  --title="What do you want to run?" --radiolist \
  --column="" --column="Description" \
   TRUE "$OPTION1" \
   FALSE "$OPTION2" \
   FALSE "$OPTION3"`

echo $SELECT
if [ "$SELECT" == "$OPTION1" ]; then
cd /mnt/utmp/thetube/bin/
python thetube.py -f -p
fi
if [ "$SELECT" == "$OPTION2" ]; then
cd /mnt/utmp/thetube/bin/
python thetube.py -f -p -m
fi
if [ "$SELECT" == "$OPTION3" ]; then
cd /mnt/utmp/thetube/bin/
./youtube-dl -U &> /tmp/youtube-dl_update
cat /tmp/youtube-dl_update | zenity --text-info --width=360 --height=240
fi
