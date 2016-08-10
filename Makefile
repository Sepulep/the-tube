all:  youtube-dl pnd

PND_MAKE=/usr/pandora/scripts/pnd_make.sh

youtube-dl:
	curl -L https://yt-dl.org/downloads/latest/youtube-dl -o youtube-dl
	chmod a+rwx thetube/bin
	mv youtube-dl thetube/bin/youtube-dl
	chmod a+wx thetube/bin/youtube-dl
	sha256sum thetube/bin/youtube-dl
	@echo see https://rg3.github.io/youtube-dl/download.html

pnd:
	${PND_MAKE} -d ./thetube -p thetube.pnd -c -x thetube/PXML.xml -i thetube/icon.png

clean:
	rm -f thetube/bin/youtube-dl thetube.pnd
