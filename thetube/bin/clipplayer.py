import time
import os
import gtk
import gobject
from subprocess import call,Popen,PIPE
from optparse import OptionParser

gtk.gdk.threads_init()

from thetube import video_player,ytdl,configuration_manager

class LocalClipboard(object):
  XA_PRIMARY='primary'
  XA_SECONDARY='secondary'
  XA_CLIPBOARD='clipboard'

  has_xclip=False
  has_xsel=False

  def __init__(self,display=":0.0",all_selections=False):
    self.display=display
    if call("which xsel > /dev/null",shell=True) == 0:
      self.has_xsel=True
    if call("which xclip > /dev/null",shell=True) == 0:
      self.has_xclip=True
    try:
      os.putenv("DISPLAY",display)
      import gtk
      self.gtk=gtk
      self.has_gtk=True
    except Exception as ex:
      print ex
      self.has_gtk=False
    if self.has_gtk:
      self.get=self.get_gtk
      self.set=self.set_gtk  
    elif self.has_xclip:
      self.get=self.get_xclip  
      self.set=self.set_xclip
    elif self.has_xsel:
      self.get=self.get_xsel  
      self.set=self.set_xsel
    else:
      raise Exception("no xclip or xsel or gtk")
    self.old=[]
    self.selections=['primary']
    if all_selections:
      self.selections=['primary','secondary','clipboard']
    for sel in range(len(self.selections)):
      self.old.append(self.get(sel=sel))

  def get_xclip(self,sel=0):
    proc = Popen('xclip -display '+self.display+' -selection '+(self.selections[sel])+' -o', stdout=PIPE,shell=True)
    content=proc.communicate()[0]
    return content
  def set_xclip(self,data,sel=0):
    proc = Popen('xclip -display '+self.display+' -selection '+(self.selections[sel])+' -i', stdin=PIPE,shell=True)
    proc.communicate(data)
  def get_xsel(self,sel=0):
    proc=Popen('xsel --display '+self.display+' --'+(self.selections[sel])+' -o', stdout=PIPE,shell=True)
    content=proc.communicate()[0]
    return content
  def set_xsel(self,data,sel=0):
    proc=Popen('xsel --display '+self.display+' --'+(self.selections[sel])+' -i', stdin=PIPE,shell=True)
    proc.communicate(data)
  def get_gtk(self,sel=0):
    with gtk.gdk.lock:
      content=self.gtk.Clipboard(selection=self.selections[sel].upper()).wait_for_text()
    if content is None:
      content=""
    return content
  def set_gtk(self,data,sel=0):
    with gtk.gdk.lock:
      cb = self.gtk.Clipboard( selection=self.selections[sel].upper() )
      cb.set_text(data)

class clipplayer(object):  
  def __init__(self,fullscreen=False,preload_ytdl=False,vo_driver='xv',
                 player="mpv",yt_fetcher="pafy",magic_string="stop"):
    config=configuration_manager.read_config()
  
    bandwidth=config.setdefault("bandwidth","360p")
    use_http=True if player=='mplayer' else False
  
    self.player=video_player(player, fullscreen=fullscreen, vo_driver=vo_driver, keep_aspect=False)
    self.yt=ytdl(yt_fetcher=yt_fetcher,preload_ytdl=preload_ytdl,
            bandwidth=bandwidth,use_http=use_http)
  
    self.c=LocalClipboard(all_selections=True)
    self.c.set('stop',sel=2)
    time.sleep(0.6)
    self.c.set(' ',sel=2)
    self.sold=""
    self.magic_string=magic_string
  def error(self,data):
    with gtk.gdk.lock:  
      md = gtk.MessageDialog(None, 
                0, gtk.MESSAGE_INFO, 
                gtk.BUTTONS_OK, data)
      gtk.timeout_add(5000,md.destroy)
      md.run()
      md.destroy()
    #~ proc = Popen('zenity --timeout 5 --warning --text="'+data+'"', stdin=PIPE,shell=True)
    #~ proc.communicate(data)

  def check_clipboard(self):
    s=self.c.get(sel=2)
    if s.startswith(self.magic_string):
      self.error("shutting down The Tube clipboard player")
      gtk.main_quit()
      return False
    if s!=self.sold:
      if s.lstrip().startswith("http"):
        self.c.set("retrieving video url of "+s.lstrip())
        try:
          url=self.yt.get_video_url(s)
        except Exception as ex:
          url="FAIL"
          self.error("The Tube playback failure: "+str(ex))
        if not url.startswith("FAIL"):
          self.player.play_url([url])
          self.c.set("done playing (copy 'stop' to the clipboard to stop The Tube)",sel=2)
        else:
          self.c.set(url+"(copy 'stop' to the clipboard to stop The Tube)",sel=2)
        self.yt.restart()
      self.sold=s
    return True

def new_option_parser():
    result = OptionParser(usage="usage: %prog [options]")
    result.add_option("-f", action="store_true", dest="fullscreen",
                      help="run fullscreen (recommend 800x480)",default=False)
    result.add_option("-p", action="store_true", dest="preload_ytdl",
                      help="preload youtube-dl",default=False)
    result.add_option("-v", action="store", dest="player",
                      help="video player to use (mpv or mplayer)",default='mplayer')
    result.add_option("-d", action="store", dest="video_driver",
                      help="driver to use (eg xv, x11) ",default='xv')
    result.add_option("-y", action="store", dest="yt_fetcher",
                      help="youtube query to use (youtube-dl or pafy) ",default='youtube-dl')
    result.add_option("-m", action="store", dest="magic_string",
                      help="magic string to terminate",default='stop')

    return result

if __name__=="__main__":
  (options, args) = new_option_parser().parse_args()  
  print options

  application=clipplayer( fullscreen=options.fullscreen,preload_ytdl=options.preload_ytdl,
    vo_driver=options.video_driver,player=options.player,yt_fetcher=options.yt_fetcher,
    magic_string=options.magic_string)

  gtk.timeout_add(500,application.check_clipboard)
  gtk.main()
