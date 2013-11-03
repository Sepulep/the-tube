#!/usr/bin/python

import gtk
import pango
import os
import urllib
import urllib2
from cStringIO import StringIO
import threading
import json
import gobject
import subprocess
import sys
import datetime
import atexit
from optparse import OptionParser

#gobject.threads_init() 
gtk.gdk.threads_init()

COL_TITLE = 0
COL_PIXBUF = 1
COL_ITEM = 2
COL_TOOLTIP = 3
COL_ORDER =4

THUMBXSIZE=116
THUMBYSIZE=90

BANDWIDTH=[18,36,5,17]

NPERPAGE=24

FULLSCREEN=False

PRELOAD_YTDL=True

def kill_process(x):
  if x.poll() is None:
    x.kill()

def get_video_url(url="",novideo=False,bandwidth="5",preload=False,yt_dl=None):
    
    if novideo and not preload: 
      bandwidth="5/18/43"
    
    if yt_dl is None:
      call = "./youtube-dl -g -f " + bandwidth + " -a -"
      print call
      yt_dl = subprocess.Popen(call, stdout = subprocess.PIPE, stderr = subprocess.PIPE,
        stdin=subprocess.PIPE, shell=True)
      atexit.register(kill_process,yt_dl)

    if preload:
      return yt_dl
    
    (url, err) = yt_dl.communicate(input=url)
        
    if yt_dl.returncode != 0:
      sys.stderr.write(err)
      raise RuntimeError('Error getting URL.')

    return url
    
def play_url(url, player="mplayer",novideo=False, fullscreen=False):
    assert player in ["mplayer"]
    if player == "mplayer":
        play_url_mplayer(url,novideo,fullscreen)
    
def play_url_mplayer(url,novideo=False,fullscreen=False):
    if novideo:
      player = subprocess.Popen(
            ['mplayer', '-quiet', '-novideo', '--', url.decode('UTF-8').strip()])
    else:
      player = subprocess.Popen(
            ['mplayer', '-fs' if fullscreen else ' ','--', url.decode('UTF-8').strip()])
    atexit.register(kill_process,player)
    player.wait()
    print "playing done"
        
def search_feed(terms):
    def fetch_cb(start, maxresults, ordering):
        url = 'https://gdata.youtube.com/feeds/api/videos'
        query = {
            'q': terms,
            'v': 2,
            'alt': 'jsonc',
            'start-index': start,
            'max-results': maxresults,
            'orderby': ordering,
        }
        try:
          sock=None
          sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
          result=json.load(sock)
        except:
          result=dict(data=dict(totalItems=0,startIndex=0,itemsPerPage=0))
        finally:  
          if sock:
            sock.close()
        return result

    return { 'fetch_cb': fetch_cb, 'description': 'search for "%s"' % (terms,) }


def standard_feed(feed_name="most_popular"):
    def fetch_cb(start, maxresults, ordering):
        url = 'https://gdata.youtube.com/feeds/api/standardfeeds/%s' % (feed_name,)
        query = {
            'v': 2,
            'alt': 'jsonc',
            'start-index': start,
            'max-results': maxresults,
            'orderby': ordering,
        }
        try:
          sock=None
          sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
          result=json.load(sock)
        except:
          result=dict(data=dict(totalItems=0,startIndex=0,itemsPerPage=0))
        finally:  
          if sock:
            sock.close()
        return result

    feed = { 'fetch_cb': fetch_cb, 'description': 'standard feed' }

    if feed_name == 'most_viewed':
        feed['description'] = 'most viewed'

    return feed

class TheTube(gtk.Window): 
    def __init__(self, fullscreen=False,preload_ytdl=False,bandwidth=[5]):
        self.showfullscreen=fullscreen
        self.preload_ytdl=preload_ytdl
        self.bandwidth='/'.join(map(lambda x:str(x), bandwidth))
        self.playing=False

        self.ordering=0
        self.order_dict=dict(relevance="relevance",published="last uploaded",viewCount="most viewed",rating="rating")
        self.orderings=["relevance","published","viewCount","rating"]

        super(TheTube, self).__init__()        
        self.set_size_request(800, 480)
        self.set_position(gtk.WIN_POS_CENTER)
        
        self.connect("destroy", gtk.main_quit)
        self.set_title("TheTube")
        if self.showfullscreen:
          self.fullscreen()
          
        vbox = gtk.VBox(False, 0)
       
        toolbar = gtk.HBox()
        toolbar.set_size_request(780,36)
        vbox.pack_start(toolbar, False, False, 0)

        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_HELP, gtk.ICON_SIZE_MENU)
        helpButton = gtk.Button()
        helpButton.add(image)
        toolbar.pack_start(helpButton,False,False,0)

        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_GO_BACK, gtk.ICON_SIZE_MENU)
        backButton = gtk.Button()
        backButton.add(image)
        toolbar.pack_start(backButton,False,False,0)
        backButton.set_sensitive(False)

        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_GO_FORWARD, gtk.ICON_SIZE_MENU)
        forwardButton = gtk.Button()
        forwardButton.add(image)
        toolbar.pack_start(forwardButton,False,False,0)
        forwardButton.set_sensitive(False)

        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_HOME, gtk.ICON_SIZE_MENU)
        homeButton = gtk.Button()
        homeButton.add(image)
        toolbar.pack_start(homeButton,False,False,0)

        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_SORT_ASCENDING, gtk.ICON_SIZE_MENU)
        sortButton = gtk.Button()
        sortButton.add(image)
        toolbar.pack_start(sortButton,False,False,0)


        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_QUIT, gtk.ICON_SIZE_MENU)
        exitButton = gtk.Button()
        exitButton.add(image)
        toolbar.pack_end(exitButton,False,False,0)

        helpButton.connect("clicked", self.on_help)
        homeButton.connect("clicked", self.on_home)
        exitButton.connect("clicked", gtk.main_quit)
        forwardButton.connect("clicked", self.on_forward)
        backButton.connect("clicked", self.on_back)
        sortButton.connect("clicked", self.on_order)


        self.homeButton=homeButton
        self.exitButton=exitButton
        self.forwardButton=forwardButton
        self.backButton=backButton

        entry = gtk.Entry(150)
        entry.modify_font(pango.FontDescription("sans 9"))
        entry.connect("activate", self.on_search, entry)
        self.entry=entry
        toolbar.pack_end(entry,True,True,0)

        self.missing= gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, THUMBXSIZE,THUMBYSIZE)
        self.missing.fill(0x0)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_NONE)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        vbox.pack_start(sw, True, True, 0)

        message=gtk.Label(" ")
        message.set_single_line_mode(True)
        message.set_size_request(780,20)
        message.modify_font(pango.FontDescription("sans 9"))

        vbox.pack_start(message,False,False,0)
        self.message=message
        
        iconView = gtk.IconView()
        iconView.set_row_spacing(0)
        iconView.set_column_spacing(0)
        iconView.set_columns(6)
        iconView.set_border_width(0)

        iconView.set_pixbuf_column(COL_PIXBUF)
        iconView.set_selection_mode(gtk.SELECTION_SINGLE)

        iconView.connect("item-activated", self.on_item_activated)
        iconView.connect("selection-changed", self.on_selection_changed)
        sw.add(iconView)
        iconView.grab_focus()
        self.iconView=iconView

        self.add(vbox)
        
        self.stores=dict()
        self.set_store()

        self.message.set_text(" Welcome to The Tube!")
        gobject.timeout_add(2000, self.on_help)

        self.connect('key_press_event', self.on_key_press_event)

        self.yt_dl=None
        if self.preload_ytdl:
          self.yt_dl=get_video_url(preload=True,bandwidth=self.bandwidth)

        self.show_all()

            
    def create_store(self):
        store = gtk.ListStore(str, gtk.gdk.Pixbuf, gobject.TYPE_PYOBJECT, str,int)
        store.set_sort_column_id(COL_ORDER, gtk.SORT_ASCENDING)
        return store
            
    def pull_image(self,url,store,row):
        try:
          a=urllib.urlopen(url)
          s=StringIO(a.read())
        except:
          print "pull image fail"
        finally:
          if a:
            a.close()  
        contents = s.getvalue()
        loader = gtk.gdk.PixbufLoader()  
        loader.write(contents, len(contents))  
        loader.close()
        pixbuf = loader.get_pixbuf()
        w=pixbuf.get_width()  
        h=pixbuf.get_height()
        x=max(0,(w-THUMBXSIZE)/2+1)
        y=max(0,(h-THUMBYSIZE)/2+1)
        cropped=pixbuf.subpixbuf(x,y,min(THUMBXSIZE,w-x),min(THUMBYSIZE,h-y))
        store.set(row, COL_PIXBUF, cropped)  
    
    def set_store(self, search=None, page=1, ordering="relevance"):
        store=self.stores.setdefault( (search,page,ordering), self.fetch_store(search,page,ordering))
        self.ordering=ordering
        self.feed_mesg=store['message']
        self.update_mesg()
        self.iconView.set_model(store['store'])
        self.store=store
        self.current_key=(search,page,ordering)

        self.backButton.set_sensitive(False if store['istart']==1 else True)    
        self.forwardButton.set_sensitive(False if store['last']>=store['ntot'] else True)    
        self.iconView.set_cursor(0)
    
    def fetch_store(self, search=None, page=1, ordering="relevance"):

        store=self.create_store()

        if search == None:
          feed=standard_feed()
        else:
          feed=search_feed(search)

        f=feed['fetch_cb'](1+(page-1)*NPERPAGE,NPERPAGE, ordering)

        istart=f['data']['startIndex']        
        ntot=f['data']['totalItems']
        if len(f['data']['items'])<NPERPAGE:
          ntot=len(f['data']['items'])
        npp=f['data']['itemsPerPage']
        last=istart-1+min(ntot,npp)

        if ntot>0:
          items= f['data']['items']
          
          message=feed['description']+": showing %i - %i out of %i, ordered by %s"%(istart,last,ntot,self.order_dict[ordering])
  
          for i,item in enumerate(items):
            url=item['thumbnail']['sqDefault']
            timestring=str(datetime.timedelta(seconds=item['duration']))
            tooltip="["+item['uploader']+"]["+timestring+"]"+item['title']
            row=store.append([item['title'], self.missing, item,tooltip,i])
            t=threading.Thread(target=self.pull_image, args=(url,store,row))
            t.daemon=True
            t.start()
        else:
          message=feed['description']+": no results"
          
        store=dict(store=store, message=message, istart=istart,ntot=ntot,last=last)
                  
        return store
        
    def on_search(self,widget,entry):
        self.set_store(search=entry.get_text(),ordering=self.orderings[0])
        self.iconView.grab_focus()
        
    def on_home(self, widget=None):
        self.set_store()
    
    def on_forward(self,widget=None):
        search,page,ordering=self.current_key
        if self.store['last']<self.store['ntot']:    
          self.set_store( search, page+1, ordering )

    def on_order(self,widget=None):
        search,page,ordering=self.current_key
        new_ordering=self.orderings[ (self.orderings.index(ordering)+1)%len(self.orderings)]
        self.set_store( search, 1, new_ordering)
      
    def on_back(self,widget=None):
        search,page,ordering=self.current_key
        if self.store['istart']>1:    
          self.set_store( search, page-1, ordering )
    
    def on_item_activated(self, widget, item):
        model = widget.get_model()
        title = model[item][COL_TITLE]
        print "click on:", title

        if self.playing:
           print "ignore"
           return
        self.playing=True

        url = model[item][COL_ITEM]['player']['default']
        print 'Playing ' + url
        

        t=threading.Thread(target=self.play, args=(url,title))
        t.daemon=True
        t.start()

    def on_selection_changed(self, widget):
         item=self.iconView.get_selected_items()[0]
         model = self.iconView.get_model()
         self.message.set_text(model[item][COL_TOOLTIP])

    def update_mesg(self):
         if self.feed_mesg:
           self.message.set_text(self.feed_mesg)
 
    def busy_message(self,arg):
        ibusy=arg[1]
        title=arg[0]
        ibusy+=1  
        self.message.set_text("busy buffering "+title[:60]+" "+(ibusy%4)*'.'+(3-ibusy%4)*' ')
        if self.playing:
          gobject.timeout_add(1000, self.busy_message,(title,ibusy))

    def play(self,url,title):
        gobject.timeout_add(1000, self.busy_message,(title,0))
        url=get_video_url(url,bandwidth=self.bandwidth,yt_dl=self.yt_dl)
        play_url(url,fullscreen=self.fullscreen)
        self.message.set_text("stopped playing "+title)
        self.playing=False
        gobject.timeout_add(2000, self.update_mesg)
        if self.preload_ytdl:
          self.yt_dl=get_video_url(preload=True,bandwidth=self.bandwidth)

    def on_help(self,widget=None):        
        self.message.set_text("'h' = help, 's' = search, 'n' = next results, 'p' = previous results,"+
           " 'o'= change order, 'enter' = play, 'q' = quit")
        gobject.timeout_add(5000, self.update_mesg)

    def on_key_press_event(self,widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
#        print "Key %s (%d) was pressed" % (keyname, event.keyval)
        if keyname in ["Up","Down"] and not self.iconView.is_focus():
          self.iconView.grab_focus()
          return True
        if keyname in ["Page_Down"]:
          self.on_forward()
        if keyname in ["Page_Up"]:
          self.on_back()
        if self.entry.is_focus():
          return False
        if keyname in ["s","S"]:
          self.update_mesg()
          self.entry.grab_focus()
          return True
        if keyname in ["n","N"]:
          self.on_forward()
        if keyname in ["p","P"]:
          self.on_back()
        if keyname in ["o","O"]:
          self.on_order()
        if keyname in ["Q","q","Escape"]:
          gtk.main_quit()
        if keyname in ["h","H"]:
          self.on_help()

    def __del__(self):
        ts=threading.enumerate()
        for t in ts[1:]:
          if t.isAlive():
            t._Thread__stop()

def new_option_parser():
    result = OptionParser(usage="usage: %prog [options]")
    result.add_option("-f", action="store_true", dest="fullscreen",
                      help="run fullscreen (recommend 800x480)",default=False)
    result.add_option("-p", action="store_true", dest="preload_ytdl",
                      help="preload youtube-dl",default=False)
    result.add_option("-q", action="store_true", dest="low_quality",
                      help="prefer low quality (240p)",default=False)
    return result

if __name__=="__main__":
  (options, args) = new_option_parser().parse_args()  
  print options
  if options.low_quality:
    BANDWIDTH=[5,17,18,36]
  else:
    BANDWIDTH=[18,36,5,17]

  TheTube( fullscreen=options.fullscreen,preload_ytdl=options.preload_ytdl,bandwidth=BANDWIDTH)
  gtk.main()
