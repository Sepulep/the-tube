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

ENCODING480p=[35]
ENCODING360p=[18]
ENCODING240p=[36,5]

NPERPAGE=24

FULLSCREEN=False

PRELOAD_YTDL=True

NSTRING=110

def truncate(string,nstring=NSTRING):
  return (string[:nstring] + '..') if len(string) > (nstring+2) else string

def kill_process(x):
  if x.poll() is None:
    x.kill()

def get_video_url(url="",bandwidth="5",preload=False,yt_dl=None):

    if yt_dl is None:
      call = "./youtube-dl -g -f " + bandwidth + " -a -"
      print call
      yt_dl = subprocess.Popen(call, stdout = subprocess.PIPE,stderr=subprocess.PIPE,
        stdin=subprocess.PIPE, shell=True)
      atexit.register(kill_process,yt_dl)

    if preload:
      return yt_dl
    
    (url, err) = yt_dl.communicate(input=url)
    if yt_dl.returncode != 0:
      sys.stderr.write(err)
      raise RuntimeError('Error getting URL.')

    return url

def download_video(url, download_directory, progressbar, bandwidth="5"):
    
    call = "./youtube-dl --newline --restrict-filenames -f " + bandwidth + \
         " -o '"+download_directory+"/%(uploader)s_%(title)s.%(ext)s' -a -"
    print call
    yt_dl = subprocess.Popen(call, stdout = subprocess.PIPE,stderr=subprocess.PIPE,
      stdin=subprocess.PIPE, shell=True)
    atexit.register(kill_process,yt_dl)
    
    yt_dl.stdin.write(url)
    yt_dl.stdin.close()
    out="1"
    destination="destination file unknown"
    while out:
      out=yt_dl.stdout.readline()
      if out.find("[download]")<0:
        continue
      if out.find("has already been downloaded")>=0:  
        destination=out.split()[1]
        return truncate(destination,NSTRING-17)+" already exists"
      if out.find("Destination")>=0:
        destination=out.split()[2]
        progressbar.set_text(truncate(destination))
      else:
        percent=float(out.split()[1][:-1])
        progressbar.set_fraction(percent/100.)  
    err=yt_dl.stderr.readlines()
    yt_dl.wait()
    if yt_dl.returncode != 0:
      sys.stderr.write(err)
      raise RuntimeError('Error getting URL.')
    print "end"
    return "download finished: "+ destination
    
def play_url(url, player="mplayer",novideo=False, fullscreen=False, omapfb=False):
    assert player in ["mplayer"]
    if player == "mplayer":
        play_url_mplayer(url,novideo,fullscreen,omapfb)
    
def play_url_mplayer(url,novideo=False,fullscreen=False, omapfb=False):
    if novideo:
      call = ['mplayer', '-quiet', '-novideo', '--', url.decode('UTF-8').strip()]
    else:
      call = ['mplayer', '-quiet']
      if fullscreen:
        call.extend(['-fs'])
      if omapfb:
        call.extend(['-vo','omapfb'])
      call.append('--')
      call.append(url.decode('UTF-8').strip())
    player = subprocess.Popen(call)
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
    def __init__(self, fullscreen=False,preload_ytdl=False,omapfb=False,bandwidth=[5]):
        self.showfullscreen=fullscreen
        self.preload_ytdl=preload_ytdl
        self.bandwidth=bandwidth
        self.playing=False
        self.feed_mesg=""
        self.download_directory=os.getenv("HOME")+"/movie"
        self.omapfb=omapfb
        self.current_downloads=set()

        self.ordering=0
        self.order_dict=dict(relevance="relevance",published="last uploaded",viewCount="most viewed",rating="rating")
        self.orderings=["relevance","published","viewCount","rating"]

        super(TheTube, self).__init__()        
        self.set_size_request(800, 480)
        self.set_position(gtk.WIN_POS_CENTER)
        
        self.connect("destroy", gtk.main_quit)
        self.set_title("The Tube")
        if self.showfullscreen:
          self.fullscreen()
          
        vbox = gtk.VBox(False, 0)
        self.vbox = vbox
       
        toolbar = gtk.HBox()
        toolbar.set_size_request(780,34)
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
        image.set_from_stock(gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_MENU)
        dirButton = gtk.Button()
        dirButton.add(image)
        toolbar.pack_start(dirButton,False,False,0)

        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_QUIT, gtk.ICON_SIZE_MENU)
        exitButton = gtk.Button()
        exitButton.add(image)
        toolbar.pack_start(exitButton,False,False,0)

        helpButton.connect("clicked", self.on_help)
        homeButton.connect("clicked", self.on_home)
        exitButton.connect("clicked", gtk.main_quit)
        forwardButton.connect("clicked", self.on_forward)
        backButton.connect("clicked", self.on_back)
        sortButton.connect("clicked", self.on_order)
        dirButton.connect("clicked", self.on_dir)        

        self.homeButton=homeButton
        self.exitButton=exitButton
        self.forwardButton=forwardButton
        self.backButton=backButton

        button480=gtk.RadioButton(None,"480p")
        button360=gtk.RadioButton(button480,"360p")
        button240=gtk.RadioButton(button480,"240p")
#        buttontv=gtk.CheckButton("TV out")
        
        self.button480=button480
        self.button360=button360
        self.button240=button240
#        self.buttontv=buttontv
                
        button480.child.modify_font(pango.FontDescription("sans 9"))
        button360.child.modify_font(pango.FontDescription("sans 9"))
        button240.child.modify_font(pango.FontDescription("sans 9"))
#        buttontv.child.modify_font(pango.FontDescription("sans 9"))

#        self.buttontv.set_active(self.omapfb)
        self.button240.set_active(bool( set(self.bandwidth) & set(ENCODING240p)))
        self.button360.set_active(bool( set(self.bandwidth) & set(ENCODING360p))) 
        self.button480.set_active(bool( set(self.bandwidth) & set(ENCODING480p)))

                
        button480.connect("toggled", self.on_res,"480p")
        button360.connect("toggled", self.on_res,"360p")
        button240.connect("toggled", self.on_res,"240p")
#        buttontv.connect("toggled", self.on_tv)
        
#        toolbar.pack_end(buttontv,False,False,0)
        toolbar.pack_end(button240,False,False,0)
        toolbar.pack_end(button360,False,False,0)
        toolbar.pack_end(button480,False,False,0)
        
        entry = gtk.Entry(150)
        entry.modify_font(pango.FontDescription("sans 9"))
        entry.connect("activate", self.on_search, entry)
        self.entry=entry
        toolbar.pack_end(entry,True,True,0)

        self.missing= gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, THUMBXSIZE,THUMBYSIZE)
        self.missing.fill(0x151515)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_NONE)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        vbox.pack_start(sw, True, True, 0)

        message=gtk.Label(" ")
        message.set_single_line_mode(True)
        message.set_size_request(780,20)
        message.modify_font(pango.FontDescription("sans 9"))

        vbox.pack_end(message,False,False,0)
        self.message=message
        
        iconView = gtk.IconView()
        iconView.set_row_spacing(0)
        iconView.set_column_spacing(0)
        iconView.set_columns(6)
        iconView.set_border_width(0)
        iconView.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("black"))
        
#        iconView.modify_bg(gtk.STATE_SELECTED, gtk.gdk.Color(red = 0., green = 0., blue = 0.))
#        self.modify_bg(gtk.STATE_ACTIVE, gtk.gdk.Color(red = 1., green = 0., blue = 0.))
#        self.modify_bg(gtk.STATE_SELECTED, gtk.gdk.Color(red = 0., green = 1., blue = 0.))
#        self.modify_bg(gtk.STATE_PRELIGHT, gtk.gdk.Color(red = 0., green = 0., blue = 1.))
#        self.modify_bg(gtk.STATE_INSENSITIVE, gtk.gdk.Color(red = 0., green = 1., blue = 1.))


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
          self.yt_dl=get_video_url(preload=True,bandwidth=self.bandwidth_string())

        self.filechooser = gtk.FileChooserDialog('Select download directory', self.window, 
                    gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, ('Cancel', 1, 'Select', 2))
        self.filechooser.set_current_folder(self.download_directory)
 
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
    
    def set_store(self, *args, **kwargs): #search=None, page=1, ordering="relevance"):
        t=threading.Thread(target=self.set_store_background, args=args,kwargs=kwargs)
        t.daemon=True
        t.start()


    def set_store_background(self, search=None, page=1, ordering="relevance"):
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
        npp=f['data']['itemsPerPage']
        last=istart-1+min(ntot,npp)

        if ntot>0:
          items= f['data']['items']

          if len(items)<NPERPAGE:
            ntot=len(items)

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
    
    def on_res(self,widget,res):
        prev=self.bandwidth
        self.bandwidth=[]
        button480=self.button480.get_active()
        button360=self.button360.get_active()
        button240=self.button240.get_active()
        if button480: self.bandwidth.extend(ENCODING480p) 
        if button360 or button480: self.bandwidth.extend(ENCODING360p) 
        if button240 or button360 or button480: self.bandwidth.extend(ENCODING240p) 
        self.bandwidth.extend([17])
        if self.preload_ytdl and self.bandwidth!=prev:
          if self.yt_dl:
            self.yt_dl.terminate()
          self.yt_dl=get_video_url(preload=True,bandwidth=self.bandwidth_string())

    def on_tv(self,widget):
        self.omapfb=not self.omapfb
        
    def on_search(self,widget,entry):
        self.set_store(search=entry.get_text(),ordering=self.orderings[0])
        self.iconView.grab_focus()
        
    def on_home(self, widget=None):
        self.set_store()

    def on_dir(self, widget=None):
        ans=self.filechooser.run()
        if ans == 2:      
          self.download_directory=self.filechooser.get_filename()
          print self.download_directory
        self.filechooser.hide()
        
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

    def on_download(self, widget=None):
         items=self.iconView.get_selected_items()
         if items:
           item=items[0]
           model = self.iconView.get_model()
           title = model[item][COL_TITLE]
           url = model[item][COL_ITEM]['player']['default']
           if url not in self.current_downloads:
             self.current_downloads.add(url)
             print 'downloading ' + url
             t=threading.Thread(target=self.download, args=(url,title))
             t.daemon=True
             t.start()
         
    def download(self,url,title):
         progressbar=gtk.ProgressBar()
         progressbar.set_size_request(780,20)
         progressbar.modify_font(pango.FontDescription("sans 9"))
         progressbar.set_text(truncate("downloading " + title))
         self.vbox.pack_start(progressbar,False,False,0)
         progressbar.show()
         try:
           result=download_video(url,self.download_directory,progressbar,bandwidth=self.bandwidth_string())
           self.message.set_text(truncate(result))
         except:
           self.message.set_text("download "+truncate(title,NSTRING-16)+" failed")
         progressbar.destroy()
         self.current_downloads.remove(url)         

    def on_selection_changed(self, widget):
         item=widget.get_selected_items()[0]
         model = widget.get_model()
         self.message.set_text(truncate(model[item][COL_TOOLTIP]))

    def update_mesg(self):
         if self.feed_mesg:
           self.message.set_text(truncate(self.feed_mesg))
 
    def busy_message(self,ibusy, message):
        ibusy+=1  
        if self.playing:
          self.message.set_text(truncate(message,NSTRING-4)+" "+(ibusy%4)*'.'+(3-ibusy%4)*' ')
          gobject.timeout_add(1000, self.busy_message,ibusy,message)

    def play(self,url,title):
        gobject.timeout_add(1000, self.busy_message,0,truncate("busy buffering "+title))
        url=get_video_url(url,bandwidth=self.bandwidth_string(),yt_dl=self.yt_dl)
        play_url(url,fullscreen=self.showfullscreen,omapfb=self.omapfb)
        self.message.set_text(truncate("stopped playing "+title))
        self.playing=False
        gobject.timeout_add(2000, self.update_mesg)
        if self.preload_ytdl:
          self.yt_dl=get_video_url(preload=True,bandwidth=self.bandwidth_string())

    def on_help(self,widget=None):        
        self.message.set_text("'h'=help, 's'=search, 'n'=next results, 'p'=previous results,"+
          " 'o'=change order, 'enter'=play,")
        gobject.timeout_add(4000, self.message.set_text,
          "'2'= max 240p', '3'= max 360p, '4'= max 480p, 'd'=download, 'f'=set folder, 'q'=quit")   
        gobject.timeout_add(7000, self.update_mesg)

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
        if keyname in ["d","D"]:
          self.on_download()
        if keyname in ["f","F"]:
          self.on_dir()
        if keyname in ["2"]:
          self.button240.set_active(not self.button240.get_active())
        if keyname in ["3"]:
          self.button360.set_active(not self.button360.get_active())
        if keyname in ["4"]:
          self.button480.set_active(not self.button480.get_active())
#        if keyname in ["t","T"]:
#          self.buttontv.set_active(not self.buttontv.get_active())

    def bandwidth_string(self):
        return '/'.join(map(lambda x:str(x), self.bandwidth))

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
    result.add_option("-m", action="store_true", dest="omapfb",
                      help="use omapfb in mplayer",default=False)
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

  TheTube( fullscreen=options.fullscreen,preload_ytdl=options.preload_ytdl,
    bandwidth=BANDWIDTH, omapfb=options.omapfb)
  gtk.main()
