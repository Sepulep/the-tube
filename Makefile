all:  youtube-dl pnd

PND_MAKE=/usr/pandora/scripts/pnd_make.sh

youtube-dl:
	wget http://yt-dl.org/downloads/2015.12.29/youtube-dl
	chmod a+rwx thetube/bin
	mv youtube-dl thetube/bin/youtube-dl
	chmod a+wx thetube/bin/youtube-dl
	sha256sum thetube/bin/youtube-dl
	@echo afc70d067dac9d12c0f664c45a14b744ba3885eb9576ac64f44b0980523ce960

pnd:
	${PND_MAKE} -d ./thetube -p thetube.pnd -c -x thetube/PXML.xml -i thetube/icon.png

clean:
	rm -f thetube/bin/youtube-dl thetube.pnd
