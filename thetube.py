#!/usr/bin/python

import gtk
import os
import urllib
import urllib2
from cStringIO import StringIO
import threading
import json
import gobject
import subprocess
import sys


#gobject.threads_init() 
gtk.gdk.threads_init()

COL_TITLE = 0
COL_PIXBUF = 1
COL_ITEM = 2
COL_TOOLTIP = 3
COL_ORDER =4

#from yt import search, standard_feed

lock=threading.Lock()

THUMBXSIZE=116
THUMBYSIZE=90

BANDWIDTH=[18,43,36,5,17]

def get_video_url(url,novideo=False,bandwidth="5"):
    
    if novideo: 
      bandwidth="5/18/43"
    
    call = "./youtube-dl -g -f " + bandwidth + " " + url
    
    yt_dl = subprocess.Popen(call, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
    (url, err) = yt_dl.communicate()
        
    if yt_dl.returncode != 0:
      sys.stderr.write(err)
      raise RuntimeError('Error getting URL.')

    return url
    
def play_url(url, player="mplayer",novideo=False):
    assert player in ["mplayer"]
    if player == "mplayer":
        play_url_mplayer(url,novideo)
    
def play_url_mplayer(url,novideo=False):
    if novideo:
      player = subprocess.Popen(
            ['mplayer', '-quiet', '-novideo', '--', url.decode('UTF-8').strip()])
    else:
      player = subprocess.Popen(
            ['mplayer', ' ','--', url.decode('UTF-8').strip()])
    player.wait()
    print "playing done"
        
def search(terms):
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
          sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
          result=json.load(sock)
        except:
          result={}
        finally:  
          if sock:
            sock.close()
        return result

    return { 'fetch_cb': fetch_cb, 'description': 'search for "%s"' % (terms,) }


def standard_feed(feed_name):
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
          sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
          result=json.load(sock)
        except:
          result={}
        finally:  
          if sock:
            sock.close()
        return result

    feed = { 'fetch_cb': fetch_cb, 'description': '??? standard feed' }

    if feed_name == 'most_viewed':
        feed['description'] = 'most viewed'

    return feed

class TheTube(gtk.Window): 
    def __init__(self):
        super(TheTube, self).__init__()
        
        self.set_size_request(800, 480)
        self.set_position(gtk.WIN_POS_CENTER)
        
        self.connect("destroy", gtk.main_quit)
        self.set_title("TheTube")
#        self.fullscreen()

        self.bandwidth='/'.join(map(lambda x:str(x), BANDWIDTH))
        
        self.current_search = None
        self.ordering="relevance"
        self.playing=False

        vbox = gtk.VBox(False, 0);
       
        toolbar = gtk.Toolbar()
        vbox.pack_start(toolbar, False, False, 0)

        backButton= gtk.ToolButton(gtk.STOCK_GO_BACK)
        backButton.set_is_important(True)
        backButton.set_sensitive(False)
        backButton.set_label("")
        toolbar.insert(backButton, -1)

        forwardButton= gtk.ToolButton(gtk.STOCK_GO_FORWARD)
        forwardButton.set_is_important(True)
        forwardButton.set_sensitive(False)
        forwardButton.set_label("")
        toolbar.insert(forwardButton, -1)

        self.upButton = gtk.ToolButton(gtk.STOCK_GO_UP);
        self.upButton.set_is_important(True)
        self.upButton.set_sensitive(False)
#        toolbar.insert(self.upButton, -1)

        homeButton = gtk.ToolButton(gtk.STOCK_HOME)
        homeButton.set_is_important(True)
        homeButton.set_label("")
        toolbar.insert(homeButton, -1)

        exitButton = gtk.ToolButton(gtk.STOCK_QUIT)
        exitButton.set_is_important(True)
        exitButton.set_label("")
        toolbar.insert(exitButton, -1)

        item = gtk.ToolItem()
        entry = gtk.Entry(150)
        entry.set_width_chars(30)
        item.add(entry)
        entry.connect("activate", self.search, entry)
        toolbar.insert(item, -1)

#        item = gtk.ToolItem()
#        label=gtk.Label("TheTube")
#        label.set_justify( gtk.JUSTIFY_RIGHT)
#        item.add(label)
#        toolbar.insert(item, -1)


#        self.missing= self.get_icon(gtk.STOCK_MISSING_IMAGE)
        self.missing= gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, THUMBXSIZE,THUMBYSIZE)
        self.missing.fill(0x0)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_NONE)
#        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        vbox.pack_start(sw, True, True, 0)

        message=gtk.Label(" ")
        message.set_single_line_mode(True)
        vbox.pack_start(message,False,False,0)
        self.message=message


        self.store = self.create_store()
        self.fill_store()

        iconView = gtk.IconView(self.store)
        iconView.set_row_spacing(0)
        iconView.set_column_spacing(0)
#        iconView.set_item_padding(4)
        iconView.set_columns(6)
        iconView.set_border_width(0)

        homeButton.connect("clicked", self.on_home_clicked)
        exitButton.connect("clicked", gtk.main_quit)

#        iconView.set_text_column(COL_TITLE)
        iconView.set_pixbuf_column(COL_PIXBUF)
        iconView.set_tooltip_column(COL_TOOLTIP)
        iconView.set_selection_mode(gtk.SELECTION_SINGLE)

        iconView.connect("item-activated", self.on_item_activated)
#        iconView.connect("selection-changed", self.on_selection_changed)
        sw.add(iconView)
        iconView.grab_focus()

        self.add(vbox)
        self.show_all()

    def get_icon(self, name):
        theme = gtk.icon_theme_get_default()
        return theme.load_icon(name, 48, 0)
    

    def create_store(self):
        store = gtk.ListStore(str, gtk.gdk.Pixbuf, gobject.TYPE_PYOBJECT, str,int)
        store.set_sort_column_id(COL_ORDER, gtk.SORT_ASCENDING)
        return store
            

    def pull_image(self,url,row):
#        with lock:
        try:
          a=urllib.urlopen(url)
        except:
          print "Exception"
          raise Exception
        s=StringIO(a.read())
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
        self.store.set(row, COL_PIXBUF, cropped)  
    
    def fill_store(self):
        self.store.clear()

        if self.current_search == None:
          feed=standard_feed("most_viewed")
        else:
          feed=search(self.current_search)

        f=feed['fetch_cb'](1,24,self.ordering)
        items= f['data']['items']
                
        istart=f['data']['startIndex']        
        ntot=f['data']['totalItems']
        npp=f['data']['itemsPerPage']
        
        self.feed_mesg="showing %i - %i out of %i: "%(istart,istart-1+min(ntot,npp),ntot)+feed['description']
        self.message.set_text(self.feed_mesg)

        for i,item in enumerate(items):
          url=item['thumbnail']['sqDefault']
          tooltip=item['title']+"\n"+item['uploader']+"\n\n"+ \
                  item['description'][:160]
          row=self.store.append([item['title'], self.missing, item,tooltip,i])
#          self.pull_image(url,row)
          t=threading.Thread(target=self.pull_image, args=(url,row))
          t.daemon=True
          t.start()
    
    def search(self,widget,entry):
        self.current_search=entry.get_text()
        self.fill_store()
        

    def on_home_clicked(self, widget):
        self.current_search=None
        self.fill_store()
        self.upButton.set_sensitive(True)        
    
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
         print "selection changed"
         pass

    def update_mesg(self):
         if self.feed_mesg:
           self.message.set_text(self.feed_mesg)
           
    def play(self,url,title):
        self.message.set_text("start playing "+title)
        url=get_video_url(url,bandwidth=self.bandwidth)
        play_url(url)
        self.message.set_text("stopped playing "+title)
        self.playing=False
        gobject.timeout_add(3000, self.update_mesg)
    
    def __del__(self):
        ts=threading.enumerate()
        for t in ts[1:]:
          if t.isAlive():
            t._Thread__stop()

            
TheTube()
gtk.main()
