from optparse import OptionParser
import gtk

from clipplayer import clipplayer
from thetube import TheTube

class clipplayer_(clipplayer):
  def __init__(self,*args,**kwargs):
    self.active=False
    print args,kwargs
    super(clipplayer_,self).__init__(*args,**kwargs)
  def on_quit(self):
    self.error("Deactiviating The Tube clipboard player")
    self.active=False
  def check_clipboard(self):
    if self.active:
      return super(clipplayer_,self).check_clipboard()
    return False
  def activate(self,active=None):
    prev=self.active
    if active is None:
      self.active=not self.active
    else:
      self.active=active
    if (not prev) and self.active:
      self.reset_clipboard()
      gtk.timeout_add(500,self.check_clipboard)

class TheTube_(TheTube):
  def __init__(self,*args,**kwargs):
    super(TheTube_,self).__init__(*args,**kwargs)
    self.active=False
    self.connect("delete-event",self.on_quit)
    self.hide_all()
  def on_quit(self,widget=None,event=None):
    self.active=False
    self.hide_all()
    return True
  def __del__(self):
    search_terms=dict(sorted(self.search_terms.iteritems(), key=operator.itemgetter(1))[-100:])
    config=dict(download_directory=self.download_directory,
                      bandwidth=self.bandwidth,search_terms=search_terms,
                      default_key=self.default_key)      
    configuration_manager.write_config(config)
    ts=threading.enumerate()
    for t in ts[1:]:
      if t.isAlive():
        t._Thread__stop()    
  def activate(self,active=None):
    prev=self.active
    if active is None:
      self.active=not self.active
    else:
      self.active=active
    if (not prev) and self.active:
      self.show_all()
      self.present()
    if prev and not self.active:
      self.hide_all()


class driver(object):
  def __init__(self,clipplayer,browser):
    self.clipplayer=clipplayer
    self.browser=browser
    self.icon=gtk.StatusIcon()
    self.icon.set_from_file("../icon.png")
    self.icon.connect("popup-menu",self.popup)

    self.menu = gtk.Menu()
    self.menuitem1 = gtk.MenuItem()
    self.menuitem1.set_label(self.label())
    self.menuitem2 = gtk.MenuItem()
    self.menuitem2.set_label(self.label_browser())
    quit = gtk.MenuItem()
    quit.set_label("Quit")
    
    self.menuitem1.connect("activate", self.activate)
    self.menuitem2.connect("activate", self.activate_browser)
    quit.connect("activate", gtk.main_quit)

    self.menu.append(self.menuitem2)
    self.menu.append(self.menuitem1)
    self.menu.append(quit)
    self.menu.show_all()

  def label(self):
    return "Deactivate clipboard player" if self.clipplayer.active else "Activate clipboard player"
  def label_browser(self):
    return "Deactivate browser" if self.browser.active else "Activate browser"

  def popup(self,icon, button, time):
      self.menuitem1.set_label(self.label())  
      self.menuitem2.set_label(self.label_browser())  
      self.menu.popup(None, None, None, button,time)

  def activate(self,widget):
    self.clipplayer.activate()
    widget.set_label(self.label())

  def activate_browser(self,widget):
    self.browser.activate()
    widget.set_label(self.label_browser())


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

  clipplayer=clipplayer_( fullscreen=options.fullscreen,preload_ytdl=options.preload_ytdl,
    vo_driver=options.video_driver,player=options.player,yt_fetcher=options.yt_fetcher,
    magic_string=options.magic_string)

  browser=TheTube_( fullscreen=options.fullscreen,preload_ytdl=options.preload_ytdl,
    vo_driver=options.video_driver,player=options.player,yt_fetcher=options.yt_fetcher)

  application=driver(clipplayer,browser)  

  gtk.main()
