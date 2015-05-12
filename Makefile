all:  youtube-dl pnd

PND_MAKE=/usr/pandora/scripts/pnd_make.sh

youtube-dl:
	wget http://yt-dl.org/downloads/2015.05.10/youtube-dl
	chmod a+rwx thetube/bin
	mv youtube-dl thetube/bin/youtube-dl
	chmod a+wx thetube/bin/youtube-dl
	sha256sum thetube/bin/youtube-dl
	@echo a54c102476dede5b0c89ce612a34d1612825023928302556d42c05dad441ed02

pnd:
	${PND_MAKE} -d ./thetube -p thetube.pnd -c -x thetube/PXML.xml -i thetube/icon.png

clean:
	rm -f thetube/bin/youtube-dl thetube.pnd
