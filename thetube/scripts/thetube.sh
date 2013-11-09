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

OPTION1="run The Tube with preference for 360p"
OPTION2="run The Tube with preference for 240p"
OPTION3="update youtube-dl"
OPTION4="run The Tube for tv-out, 360p (set HW layer)"
OPTION5="run The Tube for tv-out, 240p (set HW layer)"

SELECT=`zenity --list --width=400 --height=300 \
  --title="What do you want to run?" --radiolist \
  --column="" --column="Description" \
   TRUE "$OPTION1" \
   FALSE "$OPTION2" \
   FALSE "$OPTION4" \
   FALSE "$OPTION5" \
   FALSE "$OPTION3"`

echo $SELECT
if [ "$SELECT" == "$OPTION1" ]; then
cd /mnt/utmp/thetube/bin/
python thetube.py -f -p
fi
if [ "$SELECT" == "$OPTION2" ]; then
cd /mnt/utmp/thetube/bin/
python thetube.py -f -p -q
fi
if [ "$SELECT" == "$OPTION4" ]; then
cd /mnt/utmp/thetube/bin/
python thetube.py -f -p -m
fi
if [ "$SELECT" == "$OPTION5" ]; then
cd /mnt/utmp/thetube/bin/
python thetube.py -f -p -m -q
fi
if [ "$SELECT" == "$OPTION3" ]; then
cd /mnt/utmp/thetube/bin/
./youtube-dl -U &> /tmp/youtube-dl_update
cat /tmp/youtube-dl_update | zenity --text-info --width=360 --height=240
fi
