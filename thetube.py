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

#lock=threading.Lock()

#gobject.threads_init() 
gtk.gdk.threads_init()

COL_TITLE = 0
COL_PIXBUF = 1
COL_ITEM = 2
COL_TOOLTIP = 3
COL_ORDER =4


THUMBXSIZE=116
THUMBYSIZE=90

BANDWIDTH=[18,43,36,5,17]

NPERPAGE=18

FULLSCREEN=False

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
            ['mplayer', '-fs' if FULLSCREEN else ' ','--', url.decode('UTF-8').strip()])
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
          sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
          result=json.load(sock)
        except:
          result={}
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
          sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
          result=json.load(sock)
        except:
          result={}
        finally:  
          if sock:
            sock.close()
        return result

    feed = { 'fetch_cb': fetch_cb, 'description': 'standard feed' }

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
        if FULLSCREEN:
          self.fullscreen()

        self.bandwidth='/'.join(map(lambda x:str(x), BANDWIDTH))
        
        self.playing=False

        vbox = gtk.VBox(False, 0)
       
        toolbar = gtk.Toolbar()
        toolbar.set_size_request(780,44)
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

        homeButton = gtk.ToolButton(gtk.STOCK_HOME)
        homeButton.set_is_important(True)
        homeButton.set_label("")
        toolbar.insert(homeButton, -1)

        exitButton = gtk.ToolButton(gtk.STOCK_QUIT)
        exitButton.set_is_important(True)
        exitButton.set_label("")
        toolbar.insert(exitButton, -1)

        homeButton.connect("clicked", self.on_home)
        exitButton.connect("clicked", gtk.main_quit)
        forwardButton.connect("clicked", self.on_forward)
        backButton.connect("clicked", self.on_back)

        self.homeButton=homeButton
        self.exitButton=exitButton
        self.forwardButton=forwardButton
        self.backButton=backButton

        item = gtk.ToolItem()
        item.set_expand(True)
        entry = gtk.Entry(150)
#        entry.set_width_chars(60)
        entry.modify_font(pango.FontDescription("sans 9"))
        item.add(entry)
        entry.connect("activate", self.on_search, entry)
        self.entry=entry
        toolbar.insert(item,-1)

        self.missing= gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, THUMBXSIZE,THUMBYSIZE)
        self.missing.fill(0x0)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_NONE)
#        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        vbox.pack_start(sw, True, True, 0)

        message=gtk.Label(" ")
        message.set_single_line_mode(True)
        message.set_size_request(780,20)
        message.modify_font(pango.FontDescription("sans 9"))

        vbox.pack_start(message,False,False,0)
        self.message=message

        vbox.pack_start(gtk.HSeparator(),False,False,0)

        description=gtk.Label("Welcome to The Tube")
        description.set_size_request(780,86)
        description.set_use_markup(False)
        description.set_justify(gtk.JUSTIFY_LEFT)
        description.set_line_wrap(True)
        description.set_alignment(0,0)
        description.modify_font(pango.FontDescription("sans 8"))
        vbox.pack_start(description,False,False,0)
        self.description=description
        

        iconView = gtk.IconView()
        iconView.set_row_spacing(0)
        iconView.set_column_spacing(0)
#        iconView.set_item_padding(4)
        iconView.set_columns(6)
        iconView.set_border_width(0)

#        iconView.set_text_column(COL_TITLE)
        iconView.set_pixbuf_column(COL_PIXBUF)
#        iconView.set_tooltip_column(COL_TOOLTIP)
        iconView.set_selection_mode(gtk.SELECTION_SINGLE)

        iconView.connect("item-activated", self.on_item_activated)
        iconView.connect("selection-changed", self.on_selection_changed)
        sw.add(iconView)
        iconView.grab_focus()
        self.iconView=iconView

        self.add(vbox)
        self.show_all()
        
        self.stores=dict()
        self.set_store()

        self.connect('key_press_event', self.on_key_press_event)
        
    def get_icon(self, name):
        theme = gtk.icon_theme_get_default()
        return theme.load_icon(name, 48, 0)
    

    def create_store(self):
        store = gtk.ListStore(str, gtk.gdk.Pixbuf, gobject.TYPE_PYOBJECT, str,int)
        store.set_sort_column_id(COL_ORDER, gtk.SORT_ASCENDING)
        return store
            

    def pull_image(self,url,store,row):
#        with lock:
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
        npp=f['data']['itemsPerPage']
        last=istart-1+min(ntot,npp)

        if ntot>0:
          items= f['data']['items']
  
          message=feed['description']+": showing %i - %i out of %i, ordered by %s"%(istart,last,ntot,ordering)
  
          for i,item in enumerate(items):
            url=item['thumbnail']['sqDefault']
            tooltip="["+item['uploader']+"] "+item['title']+"\n\n"+ \
                    item['description'][:200]
            row=store.append([item['title'], self.missing, item,tooltip,i])
            t=threading.Thread(target=self.pull_image, args=(url,store,row))
            t.daemon=True
            t.start()
        else:
          message=feed['description']+": no results"
          
        store=dict(store=store, message=message, istart=istart,ntot=ntot,last=last)
                  
        return store
        
    def on_search(self,widget,entry):
        self.set_store(search=entry.get_text())
        self.iconView.grab_focus()
        
    def on_home(self, widget=None):
        self.set_store()
    
    def on_forward(self,widget=None):
        search,page,ordering=self.current_key
        if self.store['last']<self.store['ntot']:    
          self.set_store( search, page+1, ordering )

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
         print "selection changed"
         item=self.iconView.get_selected_items()[0]
         model = self.iconView.get_model()
         self.description.set_text(model[item][COL_TOOLTIP])

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
  
    def on_key_press_event(self,widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        print "Key %s (%d) was pressed" % (keyname, event.keyval)
        if keyname in ["Up","Down","Left","Right"] and not self.iconView.is_focus():
          self.iconView.grab_focus()
          return True
        if keyname in ["Page_Down"]:
          self.on_forward()
        if keyname in ["Page_Up"]:
          self.on_back()
        if self.entry.is_focus():
          return False
        if keyname in ["s","S"]:
          self.entry.grab_focus()
          return True
        if keyname in ["n","N"]:
          self.on_forward()
        if keyname in ["p","P"]:
          self.on_back()
        if keyname in ["Q","q"]:
          gtk.main_quit()
              
    def __del__(self):
        ts=threading.enumerate()
        for t in ts[1:]:
          if t.isAlive():
            t._Thread__stop()

            
TheTube()
gtk.main()
