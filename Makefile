all:  youtube-dl pnd

PND_MAKE=/usr/pandora/scripts/pnd_make.sh

youtube-dl:
	wget http://yt-dl.org/downloads/2013.12.09.2/youtube-dl 
	chmod a+rwx thetube/bin
	mv youtube-dl thetube/bin/youtube-dl
	chmod a+wx thetube/bin/youtube-dl
	sha256sum thetube/bin/youtube-dl
	@echo 5ec7406db1ef1dc189c6f01429e5e5b30d26bf80e1a94fd69f47abd6f204aa21

pnd:
	${PND_MAKE} -d ./thetube -p thetube.pnd -c -x thetube/PXML.xml -i thetube/icon.png

clean:
	rm -f thetube/bin/youtube-dl thetube.pnd
