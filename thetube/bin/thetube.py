#!/usr/bin/python

DOCSTRING="""
General keyboard shortcuts:
      'h'=this help, 'i'=clip info, 's'=search, 'n'=next results, 'p'=previous results, 'o'=change order, 'enter'=play,
      '2'=max 240p', '3'=max 360p, '4'=max 480p, 'd'=download, 'f'=set download folder, 'q'=quit
Playlist commands: 
      'a'=add, 'l'=toggle view, 'r'=remove/cut, 'c'=clear, 'space'=play"
"""

import time 
import random
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
import operator

#gobject.threads_init() 
gtk.gdk.threads_init()

COL_TITLE = 0
COL_PIXBUF = 1
COL_ITEM = 2
COL_TOOLTIP = 3
COL_ORDER =4

THUMBXSIZE=116
THUMBYSIZE=90

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

def get_video_url(url="",bandwidth="5",preload=False,yt_dl=None, use_http=True):

    if yt_dl is None:
      security='' if not use_http else '--prefer-insecure'
      call = "./youtube-dl -g -f " + bandwidth + " " + security + " -a -"
      print call
      yt_dl = subprocess.Popen(call, stdout = subprocess.PIPE,stderr=subprocess.PIPE,
        stdin=subprocess.PIPE, shell=True)
      atexit.register(kill_process,yt_dl)

    if preload:
      return yt_dl
    
    (url, err) = yt_dl.communicate(input=url)
    if yt_dl.returncode != 0:
      sys.stderr.write(err)
      return "FAIL"
#      raise RuntimeError('Error getting URL.')

    return url

def download_video(url, download_directory, progressbar, bandwidth="5"):
    
    call = "./youtube-dl --newline --restrict-filenames -f " + bandwidth + \
         " -o '"+download_directory+"/%(uploader)s-%(title)s-%(id)s.%(ext)s' -a -"
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
    
def play_url(url, player="mpv",novideo=False, fullscreen=False, vo_driver="xv",keep_aspect=True):
    assert player in ["mplayer","mpv"]
    if player == "mplayer":
        play_url_mplayer(url,novideo,fullscreen,vo_driver,keep_aspect)
    if player == "mpv":
        play_url_mpv(url,novideo,fullscreen,vo_driver,keep_aspect)
    
def play_url_mplayer(url,novideo=False,fullscreen=False, vo_driver="xv",keep_aspect=True):
    
    TMPFILE="/tmp/_mplayer_playlist"
    
    f=open(TMPFILE,"w")
    for u in url:
      f.write(u.decode('UTF-8').strip()+"\n")
    f.close()  
    
    if novideo:
      call = ['mplayer', '-quiet', '-novideo', '-playlist', TMPFILE]
    else:
      call = ['mplayer', '-quiet']
      if fullscreen:
        call.extend(['-fs'])
      if vo_driver=='omapfb':
        call.extend(['-vo',vo_driver, '-fixed-vo'])
      else:
        call.extend(['-vo',vo_driver])
      call.extend(['-playlist', TMPFILE])  
    player = subprocess.Popen(call)
    atexit.register(kill_process,player)
    player.wait()
    print "playing done"

def play_url_mpv(url,novideo=False,fullscreen=False, vo_driver="xv",keep_aspect=True):
    
    TMPFILE="/tmp/_mplayer_playlist"
    
    f=open(TMPFILE,"w")
    for u in url:
      f.write(u.decode('UTF-8').strip()+"\n")
    f.close()  
    
    if novideo:
      call = ['mpv', '--really-quiet', '-no-video', '--playlist='+TMPFILE]
    else:
      call = ['mpv', '--really-quiet','--no-osc','--no-osd-bar','--osd-font-size=30']
      if fullscreen:
        call.extend(['--fs'])
      if not keep_aspect:
        call.extend(['--no-keepaspect'])
      if vo_driver=="x11":
        call.extend(['-vo',vo_driver, '--fixed-vo','--sws-scaler=mozilla_neon'])
      else:
        call.extend(['-vo',vo_driver,'--no-fixed-vo'])
      call.extend(['--playlist='+TMPFILE])  
    print call
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

def single_video_data(videoid):
    def fetch_cb():
        url = "https://gdata.youtube.com/feeds/api/videos/"+videoid
        query = {
            'v': 2,
            'alt': 'jsonc'            
        }
        try:
          sock=None
          sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
          result=json.load(sock)
        except Exception as ex:
          result=dict(data=dict())
        finally:  
          if sock:
            sock.close()
        return result

    return { 'fetch_cb': fetch_cb, 'description': 'data for "%s"' % (videoid,) }


class TheTube(gtk.Window): 
    def __init__(self, fullscreen=False,preload_ytdl=False,vo_driver="xv", video_player='mplayer'):
        config=self.read_config()
        self.showfullscreen=fullscreen
        self.preload_ytdl=preload_ytdl
        self.bandwidth=config.setdefault("bandwidth","360p")
        self.playing=False
        self.feed_mesg=""
        self.download_directory=config.setdefault("download_directory",os.getenv("HOME")+"/movie")
        self.vo_driver=vo_driver
        self.keep_aspect=False
        self.current_downloads=set()
        self.search_terms=config.setdefault("search_terms",dict())
        self.video_player=video_player
        self.use_http=True if video_player=='mplayer' else False

        self.ordering=0
        self.order_dict=dict(relevance="relevance",published="last uploaded",viewCount="most viewed",rating="rating")
        self.orderings=["relevance","published","viewCount","rating"]

        super(TheTube, self).__init__()        
        self.set_size_request(800, 480)
        self.set_position(gtk.WIN_POS_CENTER)
        
        self.connect("destroy", self.on_quit)
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
        exitButton.connect("clicked", self.on_quit)
        forwardButton.connect("clicked", self.on_forward)
        backButton.connect("clicked", self.on_back)
        sortButton.connect("clicked", self.on_order)
        dirButton.connect("clicked", self.on_dir)        

        self.homeButton=homeButton
        self.exitButton=exitButton
        self.forwardButton=forwardButton
        self.backButton=backButton
        self.helpButton=helpButton
        self.sortButton=sortButton
        self.dirButton=dirButton

        button480=gtk.RadioButton(None,"480p")
        button360=gtk.RadioButton(button480,"360p")
        button240=gtk.RadioButton(button480,"240p")
        buttontv=gtk.CheckButton("Keep ratio")
        
        self.button480=button480
        self.button360=button360
        self.button240=button240
        self.buttontv=buttontv
                
        button480.child.modify_font(pango.FontDescription("sans 9"))
        button360.child.modify_font(pango.FontDescription("sans 9"))
        button240.child.modify_font(pango.FontDescription("sans 9"))
        buttontv.child.modify_font(pango.FontDescription("sans 9"))

        self.buttontv.set_active(self.keep_aspect)
        self.button240.set_active(self.bandwidth=="240p")
        self.button360.set_active(self.bandwidth=="360p") 
        self.button480.set_active(self.bandwidth=="480p")

        button480.connect("toggled", self.on_res,"480p")
        button360.connect("toggled", self.on_res,"360p")
        button240.connect("toggled", self.on_res,"240p")
        buttontv.connect("toggled", self.on_aspect)
        
        playlistButton = gtk.Button()
        playlistButton.set_size_request(28,32)
        playlistButton.set_label("0")
        playlistButton.connect("clicked", self.on_list)        
        toolbar.pack_start(playlistButton,False,False,0)
        self.playlistButton=playlistButton

        toolbar.pack_end(buttontv,False,False,0)
        toolbar.pack_end(button240,False,False,0)
        toolbar.pack_end(button360,False,False,0)
        toolbar.pack_end(button480,False,False,0)
        
        entry = gtk.Entry(150)
        entry.modify_font(pango.FontDescription("sans 9"))

        completion = gtk.EntryCompletion()
        self.search_store = gtk.ListStore(str)
        for s,i in self.search_terms.iteritems():
            self.search_store.append([s])
        completion.set_minimum_key_length(3)
        completion.set_model(self.search_store)
        completion.set_popup_completion(False)
        completion.set_inline_completion(True)
        entry.set_completion(completion)
        completion.set_text_column(0)

        entry.connect("activate", self.on_search)
        self.entry=entry
        toolbar.pack_end(entry,True,True,0)

        self.missing= gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, THUMBXSIZE,THUMBYSIZE)
        self.missing.fill(0x151515)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_NONE)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
#        vbox.pack_start(sw, True, True, 0)

        self.infoView=gtk.TextView()
        self.infoView.set_buffer(gtk.TextBuffer())
        self.infoView.set_size_request(780,100)
        self.infoView.modify_font(pango.FontDescription("sans 8"))
        self.infoView.set_wrap_mode(gtk.WRAP_WORD)
        sw.set_no_show_all(True)
        self.infoView_sw=sw

        message=gtk.Label(" ")
        message.set_single_line_mode(True)
        message.set_size_request(780,20)
        message.modify_font(pango.FontDescription("sans 9"))

        self.message=message
        
        iconView = gtk.IconView()
        iconView.set_row_spacing(0)
        iconView.set_column_spacing(0)
        iconView.set_columns(6)
        iconView.set_border_width(0)
        iconView.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("black"))
        iconView.modify_bg(gtk.STATE_SELECTED, gtk.gdk.Color("light grey"))
        

#        iconView.modify_bg(gtk.STATE_SELECTED, gtk.gdk.Color(red = 0., green = 0., blue = 0.))
#        iconView.modify_bg(gtk.STATE_ACTIVE, gtk.gdk.Color(red = 1., green = 0., blue = 0.))
#        iconView.modify_bg(gtk.STATE_SELECTED, gtk.gdk.Color(red = 0., green = 1., blue = 0.))
#        iconView.modify_bg(gtk.STATE_PRELIGHT, gtk.gdk.Color(red = 0., green = 0., blue = 1.))
#        iconView.modify_bg(gtk.STATE_INSENSITIVE, gtk.gdk.Color(red = 0., green = 1., blue = 1.))


        iconView.set_pixbuf_column(COL_PIXBUF)
        iconView.set_selection_mode(gtk.SELECTION_SINGLE)

        iconView.connect("item-activated", self.on_item_activated)
        iconView.connect("selection-changed", self.on_selection_changed)
        iconView.grab_focus()
        self.iconView=iconView

        self.infoView_sw.add(self.infoView)
        
        self.vbox.pack_start(iconView, True, True, 0)
        self.vbox.pack_end(sw,False,False,0)
        self.vbox.pack_end(message,False,False,0)


        self.add(vbox)
        
        self.stores=dict()
        self.stores[("__playlist__",1,"")]=dict(store=self.create_store(),
                        message=self.playlist_message, istart=1,ntot=0,last=0)
        self.playlist=self.stores[("__playlist__",1,"")]['store']
        self.playlist_clipboard=self.create_store()
        self.set_store("Openpandora",1,"relevance")
        
        self.connect('key_press_event', self.on_key_press_event)

        self.yt_dl=None
        if self.preload_ytdl:
          self.yt_dl=get_video_url(preload=True,bandwidth=self.bandwidth_string(), use_http=self.use_http)

        self.filechooser = gtk.FileChooserDialog('Select download directory', self.window, 
                    gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, ('Cancel', 1, 'Select', 2))
        self.filechooser.set_current_folder(self.download_directory)
 
        self.show_all()

        self.message.set_text(" Welcome to The Tube! (type 'h' for help)")
#        gobject.timeout_add(4000, self.flash_message," Welcome to The Tube! (type 'h' for help)")
#        gobject.timeout_add(2000, self.on_help)

    def create_store(self):
        store = gtk.ListStore(str, gtk.gdk.Pixbuf, gobject.TYPE_PYOBJECT, str,int)
#        store.set_sort_column_id(COL_ORDER, gtk.SORT_ASCENDING)
        return store
            
    def pull_image(self,url,store,row):
        time.sleep(3*random.random())
        a=None
        retry=0
        while True:
          try:
            a=urllib.urlopen(url)
            s=StringIO(a.read())
          except Exception as ex:
            if a: a.close()  
            if retry>3:
              print ex
              print "pull image fail"
              return
            retry+=1
          else:
            a.close()
            break            
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

    def pull_description(self,item):
        time.sleep(3*random.random())
        f=single_video_data(item['id'])['fetch_cb']
        data=f()['data']
        if data.has_key('description'):
          item['description']=data['description']
        else:
          print data  
    
    def set_store(self, *args, **kwargs): #search=None, page=1, ordering="relevance"):
        t=threading.Thread(target=self.set_store_background, args=args,kwargs=kwargs)
        t.daemon=True
        t.start()


    def set_store_background(self, search=None, page=1, ordering="relevance"):
        store=self.stores.setdefault( (search,page,ordering), self.fetch_store(search,page,ordering))
        self.ordering=ordering
        self.feed_mesg=store['message']() if callable(store['message']) else store['message']
        self.update_mesg()
        self.iconView.set_model(store['store'])
        self.store=store
        self.current_key=(search,page,ordering)

        self.backButton.set_sensitive(False if store['istart']==1 else True)    
        self.forwardButton.set_sensitive(False if store['last']>=store['ntot'] else True)    
#        self.iconView.select_path(0)
    
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
            item['mplayer_url']=None
            timestring=str(datetime.timedelta(seconds=item['duration']))
            tooltip="["+item['uploader']+"]["+timestring+"]"+item['title']
            row=store.append([item['title'], self.missing, item,tooltip,i])
            t=threading.Thread(target=self.pull_image, args=(url,store,row))
            t.daemon=True
            t.start()

            t=threading.Thread(target=self.pull_description, args=(item,))
            t.daemon=True
            t.start()

        else:
          message=feed['description']+": no results"
          
        store=dict(store=store, message=message, istart=istart,ntot=ntot,last=last)
                  
        return store
    
    def on_res(self,widget,res):
        prev=self.bandwidth
        if self.button480.get_active(): self.bandwidth="480p"
        if self.button360.get_active(): self.bandwidth="360p"
        if self.button240.get_active(): self.bandwidth="240p"
        if self.preload_ytdl and self.bandwidth!=prev:
          if self.yt_dl:
            self.yt_dl.terminate()
          self.yt_dl=get_video_url(preload=True,bandwidth=self.bandwidth_string(), use_http=self.use_http)

    def on_aspect(self,widget):
        self.keep_aspect=not self.keep_aspect
        
    def on_search(self,widget):
        text = widget.get_text()
        if text:
            if text not in self.search_terms.keys():
                self.search_store.append([text])
                self.search_terms[text]=0
            else:
                self.search_terms[text]=self.search_terms[text]+1      
        self.set_store(search=text,ordering=self.orderings[0])
        self.iconView.grab_focus()
        
    def on_home(self, widget=None):
        self.set_store("Openpandora",1,"relevance")

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
           self.flash_cursor("red")
           return
        self.flash_cursor("green")
        self.playing=True

        url = model[item][COL_ITEM]['player']['default']
#        mplayer_url=model[item][COL_ITEM]['mplayer_url']
        item=model[item][COL_ITEM]
        print 'Playing ' + url

        t=threading.Thread(target=self.play, args=(url,title),kwargs=dict(item=item))
        t.daemon=True
        t.start()

    def on_play_playlist(self, widget=None):
        if self.playing or len(self.playlist)==0:
           print "ignore"
           return
        self.playing=True
       
        print 'Playing playlist'

        t=threading.Thread(target=self.play_playlist, args=(self.playlist,))
        t.daemon=True
        t.start()

    def playlist_message(self):
        if len(self.playlist)==0:
          return "Playlist: empty"
        else:
          nitem=len(self.playlist)
          time=0
          for item in self.playlist:
            time+=item[COL_ITEM]['duration']
          timestring=str(datetime.timedelta(seconds=time))
          return "Playlist: %i videos ["%nitem+timestring+"]"

    def on_list(self, widget=None):
        if self.iconView.get_model()!=self.playlist:
          self.prev_key=self.current_key
          self.set_store('__playlist__',1,"")
        else:
          self.set_store(*self.prev_key)

    def get_item_video_url(self, item):
        item['mplayer_url']=get_video_url( item['player']['default'],bandwidth=self.bandwidth_string(), use_http=self.use_http)
        print item['mplayer_url']

    def set_playlist_label(self):
        self.playlistButton.set_label(str(len(self.playlist)))

    def on_add(self,widget=None):
        model = self.iconView.get_model()
        if model!=self.playlist:
          items=self.iconView.get_selected_items()
          if items:
            item=items[0]
            model = self.iconView.get_model()
            row=model[item]
            self.playlist.append(row)
            self.flash_message("added "+truncate(model[item][COL_TITLE],NSTRING-18)+" to playlist")
            self.flash_cursor("blue")


            t=threading.Thread(target=self.get_item_video_url, args=(row[COL_ITEM],))
            t.daemon=True
            t.start()
                       
        elif model==self.playlist:
          if len(self.playlist_clipboard):
            items=self.iconView.get_selected_items()
            if items:
              item=items[0]
              row=model[item]
              self.playlist.insert_before(model.get_iter(item),row=self.playlist_clipboard[0])
              self.playlist_clipboard.clear()
              self.flash_message("pasted "+truncate(model[item][COL_TITLE],NSTRING-18)+" in playlist")          
        self.set_playlist_label()

          
    def on_remove(self,widget=None):
        model = self.iconView.get_model()
        if model==self.playlist:
          items=self.iconView.get_selected_items()
          if items:
            item=items[0]
            self.playlist_clipboard.clear()
            self.playlist_clipboard.append(model[item])
            self.playlist.remove(model.get_iter(item))
            self.feed_mesg=self.playlist_message()
            self.update_mesg()
        self.set_playlist_label()

    def on_clear(self):
        self.playlist.clear()
        self.set_playlist_label()
        self.feed_mesg=self.playlist_message()
        self.update_mesg()

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
         items=widget.get_selected_items()
         if items:
           item=items[0]
           model = widget.get_model()
           self.message.set_text(truncate(model[item][COL_TOOLTIP]))
           self.infoView.get_buffer().set_text(model[item][COL_ITEM]['description'])

    def flash_cursor(self,color="green"):
        self.iconView.modify_bg(gtk.STATE_SELECTED, gtk.gdk.Color(color))
        gobject.timeout_add(250, self.iconView.modify_bg,
          gtk.STATE_SELECTED, gtk.gdk.Color("light grey"))


    def flash_message(self,message):
        old=self.message.get_text()
        new=truncate(message)
        self.message.set_text(new)
        gobject.timeout_add(2000, self.update_mesg,old,new)
      
    def update_mesg(self,mesg=None,check=None):
         if check is not None and self.message.get_text()!=check:
           return
         if self.feed_mesg and mesg is None:
           self.message.set_text(truncate(self.feed_mesg))
         if mesg is not None:
           self.message.set_text(truncate(mesg))
 
    def busy_message(self,ibusy, message):
        ibusy+=1  
        if self.playing:
          self.message.set_text(truncate(message,NSTRING-4)+" "+(ibusy%4)*'.'+(3-ibusy%4)*' ')
          gobject.timeout_add(1000, self.busy_message,ibusy,message)

    def play(self,url,title,item=None):
        gobject.timeout_add(1000, self.busy_message,0,truncate("busy buffering "+title))
        if item is not None:
          mplayer_url=item['mplayer_url']
        else:
          mplayer_url=None
        if mplayer_url is None or mplayer_url=="FAIL": 
          mplayer_url=get_video_url(url,bandwidth=self.bandwidth_string(),yt_dl=self.yt_dl,use_http=self.use_http)
          if item is not None:
            item['mplayer_url']=mplayer_url
        play_url([mplayer_url],fullscreen=self.showfullscreen,vo_driver=self.vo_driver,player=self.video_player,keep_aspect=self.keep_aspect)
        self.message.set_text(truncate("stopped playing "+title))
        self.playing=False
        gobject.timeout_add(2000, self.update_mesg)
        if self.preload_ytdl:
          self.yt_dl=get_video_url(preload=True,bandwidth=self.bandwidth_string(), use_http=self.use_http)

    def play_playlist(self,playlist):
        gobject.timeout_add(1000, self.busy_message,0,truncate("busy playing playlist"))
        urllist=[]
        for item in playlist:
          if item[COL_ITEM]['mplayer_url'] is None or item[COL_ITEM]['mplayer_url'] is "FAIL":
            url=get_video_url( item[COL_ITEM]['player']['default'],bandwidth=self.bandwidth_string(), use_http=self.use_http)
            item[COL_ITEM]['mplayer_url']=url
          url=item[COL_ITEM]['mplayer_url']
          urllist.append(url)
        play_url(urllist,fullscreen=self.showfullscreen,vo_driver=self.vo_driver,player=self.video_player,keep_aspect=self.keep_aspect)
        self.message.set_text(truncate("stopped playing playlist"))
        self.playing=False
        gobject.timeout_add(2000, self.update_mesg)

    def on_help(self,widget=None):
        self.infoView.get_buffer().set_text(DOCSTRING)
        self.on_info()

    def on_info(self,widget=None):
      if self.infoView_sw.flags() & gtk.MAPPED:
        self.infoView.hide()
        self.infoView_sw.hide()
      else:  
        self.infoView_sw.show()
        self.infoView.show()
        items=self.iconView.get_selected_items()
        if items:
           self.iconView.scroll_to_path(items[0],False,0.,0.)
                    
    def on_key_press_event(self,widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
#        print "Key %s (%d) was pressed" % (keyname, event.keyval)
        if keyname in ["Up","Down"] and not self.iconView.is_focus():
          self.iconView.grab_focus()
          return True
        if keyname in ["Page_Down"]:
          self.forwardButton.emit("activate")
        if keyname in ["Page_Up"]:
          self.backButton.emit("activate")
        if self.entry.is_focus():
          return False
        if keyname in ["s","S"]:
          self.update_mesg()
          self.entry.grab_focus()
          return True
        if keyname in ["space"]:
          self.on_play_playlist()
          return True
        if keyname in ["n","N","Control_R"]:
          self.forwardButton.emit("activate")
        if keyname in ["p","P","Shift_R"]:
          self.backButton.emit("activate")
        if keyname in ["o","O"]:
          self.sortButton.emit("activate")
        if keyname in ["Q","q","Escape"]:
          self.exitButton.emit("activate")
        if keyname in ["h","H"]:
          self.helpButton.emit("activate")
        if keyname in ["d","D"]:
          self.on_download()
        if keyname in ["f","F"]:
          self.dirButton.emit("activate")
        if keyname in ["a","A"]:
          self.on_add()
        if keyname in ["r","R"]:
          self.on_remove()
        if keyname in ["k","K"]:
          self.on_aspect()
        if keyname in ["l","L"]:
          self.playlistButton.emit("activate")
        if keyname in ["c","C"]:
          self.on_clear()
        if keyname in ["i","I"]:
          self.on_info()          
        if keyname in ["2"]:
          self.button240.set_active(not self.button240.get_active())
        if keyname in ["3"]:
          self.button360.set_active(not self.button360.get_active())
        if keyname in ["4"]:
          self.button480.set_active(not self.button480.get_active())
#        if keyname in ["t","T"]:
#          self.buttontv.set_active(not self.buttontv.get_active())

    def bandwidth_string(self):
        bw_list=[]
        if self.bandwidth in ["480p"]: bw_list.extend(ENCODING480p) 
        if self.bandwidth in ["480p","360p"]: bw_list.extend(ENCODING360p) 
        if self.bandwidth in ["480p","360p","240p"]: bw_list.extend(ENCODING240p) 
        bw_list.extend([17])
        return '/'.join(map(lambda x:str(x), bw_list))

    def read_config(self):
        try:
          f=open(os.getenv("HOME")+"/.thetube","r")
          config=json.load(f)
          f.close()
        except:
          config=dict()
        return config    
          
    def write_config(self,config):
          f=open(os.getenv("HOME")+"/.thetube","w")
          config=json.dump(config,f,indent=4)
          f.close()
          
    def on_quit(self, widget=None):
        search_terms=dict(sorted(self.search_terms.iteritems(), key=operator.itemgetter(1))[-100:])
        config=dict(download_directory=self.download_directory,
                          bandwidth=self.bandwidth,search_terms=search_terms)      
        self.write_config(config)
        ts=threading.enumerate()
        for t in ts[1:]:
          if t.isAlive():
            t._Thread__stop()
        gtk.main_quit()
        
def new_option_parser():
    result = OptionParser(usage="usage: %prog [options]")
    result.add_option("-f", action="store_true", dest="fullscreen",
                      help="run fullscreen (recommend 800x480)",default=False)
    result.add_option("-p", action="store_true", dest="preload_ytdl",
                      help="preload youtube-dl",default=False)
    result.add_option("-v", action="store", dest="video_player",
                      help="video player to use (mpv or mplayer)",default='mplayer')
    result.add_option("-d", action="store", dest="video_driver",
                      help="driver to use (eg xv, x11) ",default='xv')
    return result

if __name__=="__main__":
  (options, args) = new_option_parser().parse_args()  
  print options

  application=TheTube( fullscreen=options.fullscreen,preload_ytdl=options.preload_ytdl,
    vo_driver=options.video_driver,video_player=options.video_player)
  gtk.main()
