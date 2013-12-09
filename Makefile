all:  youtube-dl pnd

PND_MAKE=/usr/pandora/scripts/pnd_make.sh

youtube-dl:
	wget http://yt-dl.org/downloads/2013.12.09.2/youtube-dl 
	mv youtube-dl thetube/bin/youtube-dl
	chmod a+wx thetube/bin/youtube-dl
	sha256sum thetube/bin/youtube-dl

pnd:
	${PND_MAKE} -d ./thetube -p thetube.pnd -c -x thetube/PXML.xml -i thetube/icon.png

clean:
	rm -f thetube/bin/youtube-dl thetube.pnd
