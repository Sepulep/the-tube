all:  youtube-dl

PND_MAKE=/usr/pandora/scripts/pnd_make.sh

youtube-dl:
	wget http://yt-dl.org/downloads/2013.11.03/youtube-dl -o thetube/bin/youtube-dl
	sha256sum thetube/bin/youtube-dl
	echo ec8d08c680cca47230da4ab8166666ec41947a8a278ecf4d7876476d6570f92a

pnd: youtube-dl
	$PND_MAKE -d ./thetube -p thetube.pnd -c -x thetube/PXML.xml -i thetube/icon.png
