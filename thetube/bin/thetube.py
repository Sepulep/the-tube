#!/usr/bin/python

DOCSTRING="""General keyboard shortcuts: 'h'=this help, 'i'=clip info, 's'=search, 'n'=next results, 'p'=previous results,
      'o'=change order, 'enter'=play, '2'=max 240p', '3'=max 360p, '4'=max 480p, 'k'= toggle keep aspect ratio, 'd'=download,
      'f'=set download folder, 'q'=quit
Playlist commands: 'a'=add, 'l'=toggle view, 'r'=remove/cut, 'c'=clear, 'space'=play"
Advanced commands: 'm'=cycle through video players, 'y'=switch youtube query library, 'alt/start'=go home & clear cache, 'Z'=set new start screen
Special search strings: 'pl:' search for playlists, 'u:user' search for uploads from 'user'
"""

import time 
from collections import namedtuple
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
import pafy
import cPickle
from iso8601duration import parse_duration

try:
  import ctypes
  from ctypes.util import find_library
  libc = ctypes.CDLL(find_library("c"))
  res_init=libc.__res_init
except:
  res_init=lambda : None

#gobject.threads_init() 
gtk.gdk.threads_init()

COL_TITLE = 0
COL_PIXBUF = 1
COL_ITEM = 2
COL_TOOLTIP = 3
#COL_ORDER =4
STORE_COLUMNS=(str, gtk.gdk.Pixbuf, gobject.TYPE_PYOBJECT, str,int)

THUMBXSIZE=116
THUMBYSIZE=90

ENCODING480p=[35]
ENCODING360p=[18]
ENCODING240p=[36,5]

NPERPAGE=48

FULLSCREEN=False

PRELOAD_YTDL=True

NSTRING=110

MAX_STORES=30
MAX_STORE_SIZE=1000

AVAILABLE_VIDEO_PLAYERS=[("mpv","x11"),("mpv","xv")]
if subprocess.call(["which","mplayer"])==0:
  AVAILABLE_VIDEO_PLAYERS.extend([("mplayer","xv"),("mplayer","omapfb")])

def truncate(string,nstring=NSTRING):
  return (string[:nstring] + '..') if len(string) > (nstring+2) else string

def kill_process(x):
  if x.poll() is None:
    x.kill()

ytfeedkey=namedtuple("ytfeedkey",["search","ordering","playlist_id"])
ytfeedkey.__new__.__defaults__=(None,"relevance",None)

class configuration_manager(object):
    @staticmethod
    def read_config():
        try:
          f=open(os.getenv("HOME")+"/.thetube","r")
          config=json.load(f)
          f.close()
        except:
          config=dict()
        return config    
          
    @staticmethod      
    def write_config(config):
          f=open(os.getenv("HOME")+"/.thetube","w")
          config=json.dump(config,f,indent=4)
          f.close()

class ytdl(object):
    def __init__(self,yt_fetcher="youtube-dl",preload_ytdl=False,use_http=True,bandwidth="480p"):
        self.yt_fetcher=yt_fetcher
        self.preload_ytdl=preload_ytdl
        self.use_http=use_http
        self.bandwidth=bandwidth
        self.preloaded_ytdl=None
        self.restart()
        self._url_cache=dict()

    def restart(self):
        if self.yt_fetcher=="youtube-dl" and self.preload_ytdl:
          self.preloaded_ytdl=self.start_ytdl(force=True)

    def get_video_url(self,url):
        key=(url,self.use_http,self.bandwidth)
        if key not in self._url_cache or self._url_cache[key].startswith("FAIL"):
          self._url_cache[key]="busy"
          if self.yt_fetcher=="youtube-dl":
            video_url=self.get_video_url_ytdl(url)
          if self.yt_fetcher=="pafy":
            video_url=self.get_video_url_pafy(url)
          self._url_cache[key]=video_url
        else:            
          while self._url_cache[key]=="busy":
            time.sleep(0.1)
        return self._url_cache[key]

    def download_video(self,url, download_directory, progressbar):
        if self.yt_fetcher=="youtube-dl":
          return self.download_video_ytdl(url, download_directory, progressbar)
        else:
          return self.download_video_ytdl(url, download_directory, progressbar)

    def start_ytdl(self,force=False):
        if self.preloaded_ytdl is not None:
          if not force:
            yt_dl=self.preloaded_ytdl
            self.preloaded_ytdl=None
            return yt_dl
          else:
            self.preloaded_ytdl.terminate()
        security='' if not self.use_http else '--prefer-insecure'
        bandwidth=self.ytdl_bandwidth_string()
        call = "./youtube-dl -g -f " + bandwidth + " " + security + " -a -"
        print call
        yt_dl = subprocess.Popen(call, stdout = subprocess.PIPE,stderr=subprocess.PIPE,
          stdin=subprocess.PIPE, shell=True)
        atexit.register(kill_process,yt_dl)
        return yt_dl

    def get_video_url_ytdl(self,url):
        yt_dl=self.start_ytdl()
        
        (url, err) = yt_dl.communicate(input=url)
        if yt_dl.returncode != 0:
          sys.stderr.write(err)
          return "FAIL"
        return url

    def get_video_url_pafy(self,url):
        try:
          v=pafy.new(url,basic=False)
          bw_list=self.yt_bandwidths()
          for b in bw_list:
            for s in v.streams:
              if int(s.itag)==b:
                url=s.url if self.use_http else s.url_https
                return url
        except Exception as ex:
          print ex
          pass
        return "FAIL get_video_url_pafy"

    def yt_bandwidths(self):
        bw_list=[]
        if self.bandwidth in ["480p"]: bw_list.extend(ENCODING480p) 
        if self.bandwidth in ["480p","360p"]: bw_list.extend(ENCODING360p) 
        if self.bandwidth in ["480p","360p","240p"]: bw_list.extend(ENCODING240p) 
        bw_list.extend([17])
        return bw_list
        
    def ytdl_bandwidth_string(self):
        bw_list=self.yt_bandwidths()
        return '/'.join(map(lambda x:str(x), bw_list))

    def download_video_ytdl(self,url, download_directory, progressbar):
        
        bandwidth=self.ytdl_bandwidth_string()
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
            return truncate(destination,NSTRING-17)+" already exists", destination
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
        return "download finished: "+ destination, destination

class video_player(object):
    def __init__(self,player="mpv",novideo=False, fullscreen=False, vo_driver="xv",keep_aspect=True):
        self.player=player
        self.novideo=novideo
        self.fullscreen=fullscreen
        self.vo_driver=vo_driver
        self.keep_aspect=keep_aspect
        self.TMPFILE="/tmp/_mplayer_playlist"
 
    def play_url(self,url):
                
        f=open(self.TMPFILE,"w")
        for u in url:
          f.write(u.decode('UTF-8').strip()+"\n")
        f.close()
        
        assert self.player in ["mplayer","mpv"]

        if self.player == "mplayer":
            call=self.call_mplayer()
        if self.player == "mpv":
            call=self.call_mpv()
        print "subprocess call:", call
        
        player = subprocess.Popen(call)
        atexit.register(kill_process,player)
        player.wait()
        print "playing done"

    def call_mplayer(self):
        call = ['mplayer', '-cache-min','50','-quiet','-playlist', self.TMPFILE]
        if self.novideo:
          call.extend(['-novideo'])
        else:
          if self.fullscreen:
            call.extend(['-fs'])
          if self.keep_aspect:
            call.extend(['-zoom','-xy','800'])
          else:
            call.extend(['-zoom','-x','800','-y','480'])            
          if self.vo_driver=='omapfb':
            call.extend(['-vo',self.vo_driver, '-fixed-vo'])
          else:
            call.extend(['-vo',self.vo_driver])
        return call
    
    def call_mpv(self):
        call=['mpv', '--quiet','--playlist='+self.TMPFILE]
        if self.novideo:
          call.extend(['-no-video'])
        else:
          call.extend(['--no-osc','--no-osd-bar','--osd-font-size=30',
                  '--cache=8000','--cache-initial=512','--framedrop=yes'])
          if self.fullscreen:
            call.extend(['--fs'])
          if not self.keep_aspect:
            call.extend(['--no-keepaspect'])
          if self.vo_driver=="x11":
            call.extend(['-vo',self.vo_driver, '--fixed-vo','--sws-scaler=mozilla_neon'])
          else:
            call.extend(['-vo',self.vo_driver,'--no-fixed-vo'])
        return call

class dummy_api(object):
    order_dict=dict(relevance="relevance")
    orderings=["relevance"]
    def get_feed(self,search=None,playlist_id=None):
      def fetch_cb(start, maxresults, ordering):
        time.sleep(0.5)
        if start>1000:
          result=dict(data=dict(totalItems=0,startIndex=0,itemsPerPage=0),exception="dummy err")
          return result
        items=[]
        for i in range(start,min(start+maxresults,1001)):
          item=dict(duration=10,uploader="none",title="dummy"+str(i),id="dummy_id",thumbnail=dict(sqDefault="none"))
          items.append(item)
        data=dict(totalItems=1000,startIndex=start,itemsPerPage=NPERPAGE,items=items)
        result=dict(data=data)
        return result
      return  { 'fetch_cb': fetch_cb, 'description': "dummy", 'type' : "search" } 
    def single_video_data(self,id_):
      def fetch_cb():
        data=dict()
        result=dict(data=data)
        return result
      return  { 'fetch_cb': fetch_cb, 'description': 'data for dummy', 'type' : "single" } 


class youtube_api_v3(object):

    order_dict=dict(relevance="relevance",date="last uploaded",viewCount="most viewed",rating="rating")
    orderings=["relevance","date","viewCount","rating"]

    def __init__(self,API_KEY=None):
      if API_KEY is None:
        f=open('API_KEY','r')
        API_KEY=f.readline()[:-1]
        f.close()
        self.API_KEY=API_KEY

    def search_info(self,search):
      result=dict()
      if search==None or search=="":
        return result
      search=search.replace("u:","user:").replace("pl:","playlist:").replace("rl:","related:")
      search=search.replace(": ",":").replace(": ",":")
      if "related:" in search:
        vid=search[search.find("related:"):].split()[0][8:]
        result["related"]=vid
        result["terms"]=vid
        return result
      if "playlist:" in search:
        result["playlist"]=True
        search=search.replace("playlist:","")
      if "user:" in search:
        user=search[search.find("user:"):].split()[0][5:]
        result["user"]=user
        search=search.replace("user:"+user,"")
      if len(search):
        result["terms"]=search
      return result
    
    def get_feed(self,search=None,playlist_id=None):
        search=self.search_info(search)
        if not search:
          if playlist_id:            
            return self.playlist_feed(playlist_id)
          else:
            return self.standard_feed()
        elif "playlist" in search:
          if "user" in search:
            return self.playlist_search_feed(search["user"],user=True)
          else:
            return self.playlist_search_feed(search["terms"],user=False)
        elif "user" in search:
          if "terms" in search:
            return self.search_feed(search["terms"],search["user"])
          else:
            return self.user_feed(search["user"])
        else:
          return self.search_feed(search["terms"])

#placeholder
    def user_feed(self,terms):
        def fetch_cb(pageToken, maxresults, ordering):
            url = 'https://www.googleapis.com/youtube/v3/search'
            query = {
                'key' : self.API_KEY,
                'q': terms,
                'part': 'id,snippet',
                'maxResults': maxresults,
                'type' : 'video',
                'order': ordering,
                'pageToken' : pageToken
            }

            try:
              print '%s?%s' % (url, urllib.urlencode(query))
              sock=None
              sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
              result=json.load(sock)
            except Exception as ex:
              print ex
              result=dict(nextPageToken="",
                pageInfo={'totalResults':0,'resultsPerPage':0},exception=str(ex))
            finally:  
              if sock:
                sock.close()
            return result
        description = 'search for user "%s"' % (terms,)
        return { 'fetch_cb': fetch_cb, 'description': description, 'type' : "search" }

              
    def search_feed(self,terms,user=None):
        def fetch_cb(pageToken, maxresults, ordering):
            url = 'https://www.googleapis.com/youtube/v3/search'
            query = {
                'key' : self.API_KEY,
                'q': terms,
                'part': 'id,snippet',
                'maxResults': maxresults,
                'type' : 'video',
                'order': ordering,
                'pageToken' : pageToken
            }

            #~ if user:
              #~ query['author']=user
            try:
              sock=None
              sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
              result=json.load(sock)
            except Exception as ex:
              result=dict(nextPageToken="",
                pageInfo={'totalResults':0,'resultsPerPage':0},exception=str(ex))
            finally:  
              if sock:
                sock.close()
            return result
        description = 'search for "%s"' % (terms,)
        if user: description=description + ' by: "%s"'%(user,) 
        return { 'fetch_cb': fetch_cb, 'description': description, 'type' : "search" }
    
    def playlist_search_feed(self,terms,user=False):
        def fetch_cb(pageToken, maxresults, ordering):
            url = 'https://www.googleapis.com/youtube/v3/search'
            query = {
                'key' : self.API_KEY,
                'q': terms,
                'part': 'id,snippet',
                'maxResults': maxresults,
                'type' : 'playlist',
                'order': ordering,
                'pageToken' : pageToken
            }
            try:
              sock=None
              sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
              result=json.load(sock)
            except Exception as ex:
              result=dict(nextPageToken="",
                pageInfo={'totalResults':0,'resultsPerPage':0},exception=str(ex))
            finally:  
              if sock:
                sock.close()
            return result
        description = 'playlist search for "%s"' % (terms,)
        feedtype="playlist-search"
        if user: 
          description=description + ' by: "%s"'%(user,) 
          feedtype="playlist-user"
        return { 'fetch_cb': fetch_cb, 'description': description, 'type' : feedtype}

    def playlist_feed(self,playlist_id):
        def fetch_cb(pageToken, maxresults, ordering):
            url = 'https://www.googleapis.com/youtube/v3/playlistItems'
            query = {
                'key' : self.API_KEY,
                'playlistId': playlist_id,
                'part': 'id,snippet',
                'maxResults': maxresults,
                'pageToken' : pageToken
            }

            #~ url = 'https://gdata.youtub
            try:
              print '%s?%s' % (url, urllib.urlencode(query))
              sock=None
              sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
              result=json.load(sock)
            except Exception as ex:
              result=dict(nextPageToken="",
                pageInfo={'totalResults':0,'resultsPerPage':0},exception=str(ex))

            finally:  
              if sock:
                sock.close()
            return result
    
        feed = { 'fetch_cb': fetch_cb, 'description': 'feed of playlist %s' % (playlist_id,), 'type' : "playlist" }

        return feed
        
    def video_data(self,videoids):
        
        def fetch_cb():
            url = "https://www.googleapis.com/youtube/v3/videos"
            query = {
                'key' : self.API_KEY,
                'id': ','.join(videoids),
                'part' : "snippet,contentDetails",
                'maxResults' : len(videoids)
            }
            try:
              sock=None
              sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
              result=json.load(sock)
            except Exception as ex:
              result=dict(nextPageToken="",
                pageInfo={'totalResults':0,'resultsPerPage':0},exception=str(ex))
            finally:  
              if sock:
                sock.close()
            return result
    
        return { 'fetch_cb': fetch_cb, 'description': 'data for "%s"' % (len(videoids),), 'type' : "single" }

    def playlist_data(self,playlistids):
        
        def fetch_cb():
            url = "https://www.googleapis.com/youtube/v3/playlists"
            query = {
                'key' : self.API_KEY,
                'id': ','.join(playlistids),
                'part' : "snippet,contentDetails",
                'maxResults' : len(playlistids)
            }
            try:
              sock=None
              sock=urllib2.urlopen('%s?%s' % (url, urllib.urlencode(query)))
              result=json.load(sock)
            except Exception as ex:
              print ex
              result=dict(nextPageToken="",
                pageInfo={'totalResults':0,'resultsPerPage':0},exception=str(ex))
            finally:  
              if sock:
                sock.close()
            return result
    
        return { 'fetch_cb': fetch_cb, 'description': 'data for "%s"' % (len(playlistids),), 'type' : "single" }


YT=youtube_api_v3()
#~ YT=dummy_api()

class TheTube(gtk.Window): 
    def __init__(self, fullscreen=False,preload_ytdl=False,vo_driver="xv", player='mplayer',yt_fetcher="youtube-dl"):
        config=configuration_manager.read_config()

        self.player=video_player(player, fullscreen=fullscreen, vo_driver=vo_driver, keep_aspect=False)

        self.bandwidth=config.setdefault("bandwidth","360p")
        self.use_http=True if player=='mplayer' else False
        self.default_key=config.setdefault("default_key",ytfeedkey("Openpandora","relevance",None))

        self.yt_dl=ytdl(yt_fetcher=yt_fetcher,preload_ytdl=preload_ytdl,
          bandwidth=self.bandwidth,use_http=self.use_http)

        self.playing=False
        self.feed_mesg=""
        self.download_directory=config.setdefault("download_directory",os.getenv("HOME")+"/movie")
        self.current_downloads=set()
        self.search_terms=config.setdefault("search_terms",dict())

        super(TheTube, self).__init__()        
        self.set_size_request(800, 480)
        self.set_position(gtk.WIN_POS_CENTER)
        
        self.connect("destroy", self.on_quit)
        self.set_title("The Tube")
        if fullscreen:
          self.fullscreen()
          
        self.vbox = gtk.VBox(False, 0)
       
        toolbar = gtk.HBox()
        toolbar.set_size_request(780,34)
        self.vbox.pack_start(toolbar, False, False, 0)
        
        def stock_button(icon,signal):
          image = gtk.Image()
          image.set_from_stock(icon, gtk.ICON_SIZE_MENU)
          button=gtk.Button()
          button.add(image)
          button.connect("clicked",signal)
          return button
        
        self.helpButton=stock_button(gtk.STOCK_HELP, self.on_help)
        self.backButton=stock_button(gtk.STOCK_GO_BACK,self.on_back)
        self.forwardButton=stock_button(gtk.STOCK_GO_FORWARD, self.on_forward)
        self.homeButton=stock_button(gtk.STOCK_HOME, self.on_home)
        self.sortButton=stock_button(gtk.STOCK_SORT_ASCENDING,self.on_order)
        self.dirButton=stock_button(gtk.STOCK_DIRECTORY,self.on_dir)
        self.exitButton=stock_button(gtk.STOCK_QUIT,self.on_quit)
 
        toolbar.pack_start(self.helpButton,False,False,0)
        toolbar.pack_start(self.backButton,False,False,0)
        toolbar.pack_start(self.forwardButton,False,False,0)
        toolbar.pack_start(self.homeButton,False,False,0)
        toolbar.pack_start(self.sortButton,False,False,0)
        toolbar.pack_start(self.dirButton,False,False,0)
        toolbar.pack_start(self.exitButton,False,False,0)

        self.backButton.set_sensitive(False)
        self.forwardButton.set_sensitive(False)

        self.button480=gtk.RadioButton(None,"480p")
        self.button360=gtk.RadioButton(self.button480,"360p")
        self.button240=gtk.RadioButton(self.button480,"240p")
        self.buttontv=gtk.CheckButton("keep aspect ")
                        
        self.button480.child.modify_font(pango.FontDescription("sans 9"))
        self.button360.child.modify_font(pango.FontDescription("sans 9"))
        self.button240.child.modify_font(pango.FontDescription("sans 9"))
        self.buttontv.child.modify_font(pango.FontDescription("sans 9"))

        self.buttontv.set_active(self.player.keep_aspect)
        self.button240.set_active(self.bandwidth=="240p")
        self.button360.set_active(self.bandwidth=="360p") 
        self.button480.set_active(self.bandwidth=="480p")

        self.button480.connect("toggled", self.on_res,"480p")
        self.button360.connect("toggled", self.on_res,"360p")
        self.button240.connect("toggled", self.on_res,"240p")
        self.buttontv.connect("toggled", self.on_aspect)
        
        playlistButton = gtk.Button()
        playlistButton.set_size_request(36,32)
        playlistButton.set_label("0")
        playlistButton.connect("clicked", self.on_list)        
        toolbar.pack_start(playlistButton,False,False,0)
        self.playlistButton=playlistButton

        toolbar.pack_end(self.buttontv,False,False,0)
        toolbar.pack_end(self.button240,False,False,0)
        toolbar.pack_end(self.button360,False,False,0)
        toolbar.pack_end(self.button480,False,False,0)
        
        self.entry = gtk.Entry(150)
        self.entry.modify_font(pango.FontDescription("sans 9"))

        completion = gtk.EntryCompletion()
        self.search_store = gtk.ListStore(str)
        for s,i in self.search_terms.iteritems():
            self.search_store.append([s])
        completion.set_minimum_key_length(3)
        completion.set_model(self.search_store)
        completion.set_popup_completion(False)
        completion.set_inline_completion(True)
        self.entry.set_completion(completion)
        completion.set_text_column(0)

        self.entry.connect("activate", self.on_search)
        toolbar.pack_end(self.entry,True,True,0)

        self.missing= gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, THUMBXSIZE,THUMBYSIZE)
        self.missing.fill(0x151515)

        self.infoView_sw = gtk.ScrolledWindow()
        self.infoView_sw.set_shadow_type(gtk.SHADOW_NONE)
        self.infoView_sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        self.infoView=gtk.TextView()
        self.infoView.set_buffer(gtk.TextBuffer())
        self.infoView.set_size_request(780,100)
        self.infoView.modify_font(pango.FontDescription("sans 8"))
        self.infoView.set_wrap_mode(gtk.WRAP_WORD)
        self.infoView_sw.set_no_show_all(True)
        self.infoView.set_property('editable', False)
        self.infoView.set_property('cursor-visible', False)

        self.message=gtk.Label(" ")
        self.message.set_single_line_mode(True)
        self.message.set_size_request(780,20)
        self.message.modify_font(pango.FontDescription("sans 9"))
        
        self.iconView = gtk.IconView()
        self.iconView.set_row_spacing(0)
        self.iconView.set_column_spacing(0)
        self.iconView.set_columns(6)
        self.iconView.set_border_width(0)
        self.iconView.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("black"))
        self.iconView.modify_bg(gtk.STATE_SELECTED, gtk.gdk.Color("light grey"))
        

#        self.iconView.modify_bg(gtk.STATE_SELECTED, gtk.gdk.Color(red = 0., green = 0., blue = 0.))
#        self.iconView.modify_bg(gtk.STATE_ACTIVE, gtk.gdk.Color(red = 1., green = 0., blue = 0.))
#        self.iconView.modify_bg(gtk.STATE_SELECTED, gtk.gdk.Color(red = 0., green = 1., blue = 0.))
#        self.iconView.modify_bg(gtk.STATE_PRELIGHT, gtk.gdk.Color(red = 0., green = 0., blue = 1.))
#        self.iconView.modify_bg(gtk.STATE_INSENSITIVE, gtk.gdk.Color(red = 0., green = 1., blue = 1.))


        self.iconView.set_pixbuf_column(COL_PIXBUF)
        self.iconView.set_selection_mode(gtk.SELECTION_SINGLE)

        self.iconView.connect("item-activated", self.on_item_activated)
        self.iconView.connect("selection-changed", self.on_selection_changed)
        self.iconView.grab_focus()

        self.infoView_sw.add(self.infoView)
        
        self.vbox.pack_start(self.iconView, True, True, 0)
        self.vbox.pack_end(self.infoView_sw,False,False,0)
        self.vbox.pack_end(self.message,False,False,0)

        self.add(self.vbox)
        
        self.reset_store()
        
        self.connect('key_press_event', self.on_key_press_event)

        self.filechooser = gtk.FileChooserDialog('Select download directory', self.window, 
                    gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, ('Cancel', 1, 'Select', 2))
        self.filechooser.set_current_folder(self.download_directory)
 
        #~ self.show_all()

        self.message.set_text(" Welcome to The Tube! (type 'h' for help)")

    def reset_store(self):
        self.stores=dict()
        self.store=None
        self.keys_for_stores=[]
        pl_key=ytfeedkey("__playlist__","",None)
        playlist=dict(store=self.create_store(),
                        message=self.playlist_message, ntot=0,
                        key=pl_key)
        self.stores[pl_key]=playlist
        self.playlist=playlist
        self.playlist_clipboard=self.create_store()
        self.set_store(*self.default_key)
    
    def create_store(self):
        store = gtk.ListStore(*STORE_COLUMNS)
#        store.set_sort_column_id(COL_ORDER, gtk.SORT_ASCENDING)
        return store
            
    def pull_image(self,row):
        url=row[COL_ITEM]['snippet']['thumbnails']['default']['url']
        time.sleep(random.random()/2)
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
#        store.set(row, COL_PIXBUF, cropped)
        row[COL_PIXBUF]=cropped
 

    def pull_playlist_image(self,row):
        time.sleep(random.random()/2)
        feed=YT.get_feed(playlist_id=row[COL_ITEM]['id'])
        fc=feed['fetch_cb']
        r=fc(1,1,"relevance")
        try:
          row[COL_ITEM]['thumbnail']=r['data']['thumbnail']
        except:
          print "fail on pull_playlist_image"
          print r['data'].keys()

        self.pull_image(row)

    def pull_description(self,item):
        time.sleep(random.random()/2)
        f=YT.single_video_data(item['id'])['fetch_cb']
        data=f()['data']
        if data.has_key('description'):
          item['description']=data['description']
        else:
          item['description']="video description not found"

    def pull_descriptions(self,rows):
        videoids=[]
        lookup=dict()
        for row in rows:
          if row[COL_ITEM]['kind']=="youtube#playlistItem":
            vid=row[COL_ITEM]['snippet']['resourceId']['videoId']
          else:
            vid=row[COL_ITEM]['id']['videoId']
          lookup[vid]=row
          videoids.append(vid)
        f=YT.video_data(videoids)['fetch_cb']
        data=f()
        ntot=data['pageInfo']['totalResults']
        if ntot>0 and 'items' in data:
          items= data['items']
          for item in items:
            lookup[item['id']][COL_ITEM]['snippet']=item['snippet']
            lookup[item['id']][COL_ITEM]['contentDetails']=item['contentDetails']
            duration=str(parse_duration(item['contentDetails']['duration']))
            lookup[item['id']][COL_TOOLTIP]="["+duration+"] "+item['snippet']['title']

    def pull_playlist_descriptions(self,rows):
        videoids=[]
        lookup=dict()
        for row in rows:
          vid=row[COL_ITEM]['id']['playlistId']
          lookup[vid]=row
          videoids.append(vid)
        f=YT.playlist_data(videoids)['fetch_cb']
        data=f()
        ntot=data['pageInfo']['totalResults']
        if ntot>0 and 'items' in data:
          items= data['items']
          for item in items:
            lookup[item['id']][COL_ITEM]['snippet']=item['snippet']
            lookup[item['id']][COL_ITEM]['contentDetails']=item['contentDetails']
            lookup[item['id']][COL_TOOLTIP]="["+str(item['contentDetails']['itemCount'])+" videos] "+item['snippet']['title']

    
    def set_store(self, search=None,ordering="relevance",playlist_id=None):
        key=ytfeedkey(search,ordering,playlist_id)
        gtk.idle_add(self.set_store_background,key)
        #~ t=threading.Thread(target=self.set_store_background,args=(key,))
        #~ t.daemon=True
        #~ t.start()

    def set_store_background(self, key):
        store=self.fetch_and_cache(key)
        self.feed_mesg=store['message']() if callable(store['message']) else store['message']
        self.update_mesg()
        self.iconView.freeze_child_notify()
        self.iconView.set_model(store['store'])
        self.iconView.thaw_child_notify()
        self.store=store
 
        try:
          i=self.keys_for_stores.index(key)
          b1=False if i==0 else True
          b2=False if i==len(self.keys_for_stores)-1 else True
          print i, len(self.keys_for_stores),b1,b2
        except:
          b1=b2=False
        self.backButton.set_sensitive(b1)    
        self.forwardButton.set_sensitive(b2)    
#        self.iconView.select_path(0)
    
    def fetch_and_cache(self, key):
        if key not in self.stores:
          self.stores[key]=self.new_store(key)
          if self.store and not self.store==self.playlist:
            i=self.keys_for_stores.index(self.store['key'])
            self.keys_for_stores.insert(i+1,key)
          else:  
            self.keys_for_stores.append(key)
          if len(self.keys_for_stores)>MAX_STORES:
            key=self.keys_for_stores.pop(0)
            self.stores.pop(key)
        return self.stores[key]
    
    def new_store(self,key):
        store=dict(store=self.create_store(),ntot=-1,nextPageToken="",key=key,message="uninit",type="uninit",
         updating=False)
        self.expand_store(store)
        return store
    
    def expand_store_background(self,_store):
        self.expand_store(_store)
        self.feed_mesg=_store['message']() if callable(_store['message']) else _store['message']
#        self.update_mesg()
    
    def expand_store(self, _store):

        if _store==self.playlist: return
        if _store["updating"]:
          print "already updating"
          return
        
        
        page=_store['nextPageToken']
        if page is None:
          return

        store=_store['store']
        key=_store['key']

        if _store['ntot']==len(store):
          print "max store reached"
          return

        _store["updating"]=True

        search,ordering,playlist_id=key

        feed=YT.get_feed(search=search,playlist_id=playlist_id)
        
                  
        f=feed['fetch_cb'](page,NPERPAGE, ordering)
        if "exception" in f:
          print "exception:", f["exception"]


        reset=False
        if _store['store']==self.iconView.get_model():
          cursor=self.iconView.get_cursor()
          #~ self.iconView.freeze_child_notify()
          #~ self.iconView.set_model(None)
          reset=True
        
        #~ print f
        #~ print f.keys()
        ntot=f['pageInfo']['totalResults']
        _store['ntot']=ntot
        if 'nextPageToken' in f:
          _store['nextPageToken']=f['nextPageToken']
        else:
          _store['nextPageToken']=None

        newrows=[]
        if ntot>0 and 'items' in f:
          items= f['items']
  
          for i,item in enumerate(items):                
            #~ if not "duration" in item:
              #~ continue
            
            #~ timestring=str(datetime.timedelta(seconds=item['duration']))
            #~ tooltip="["+item['uploader']+"]["+timestring+"]"+item['title']
            title=item['snippet']['title']
            tooltip=title
            row=store.append([title, self.missing, item,tooltip,i])
            newrows.append(store[row])
            
            t=threading.Thread(target=self.pull_image, args=(store[row],))
            t.daemon=True
            t.start()

            #~ t=threading.Thread(target=self.pull_description, args=(item,))
            #~ t.daemon=True
            #~ t.start()

            #~ for i,item in enumerate(items):
              #~ item['is_playlist']=True
              #~ tooltip="["+item['author']+"]["+str(item['size'])+" videos]"+item['title']
              #~ row=store.append([item['title'], self.missing, item,tooltip,i])
              #~ t=threading.Thread(target=self.pull_playlist_image, args=(store[row],))
              #~ t.daemon=True
              #~ t.start()

        if len(newrows)>0:
          if feed['type'] in ["playlist-search","playlist-user"]:
            t=threading.Thread(target=self.pull_playlist_descriptions, args=(newrows,))
          else:
            t=threading.Thread(target=self.pull_descriptions, args=(newrows,))
          t.daemon=True
          t.start()
          
        if _store['ntot']>0:
          if feed["type"].startswith("playlist"):
            message=feed['description']+": showing %i out of %i"%(len(store),_store['ntot'])
          else:
            message=feed['description']+": showing %i out of %i, ordered by %s"%(len(store),_store['ntot'],YT.order_dict[ordering])
        else:
          message=feed['description']+": no results"
                    
        _store['message']=message
        _store['page']=page
        _store['type']=feed["type"]
        _store['updating']=False

        if reset:
          #~ self.iconView.set_model(_store['store'])
          #~ self.iconView.thaw_child_notify()
          if cursor:
            self.iconView.set_cursor(cursor[0][0]+self.iconView.get_columns())
            self.iconView.select_path(cursor[0][0]+self.iconView.get_columns())

    
    def on_res(self,widget,res):
        if self.button480.get_active(): self.bandwidth="480p"
        if self.button360.get_active(): self.bandwidth="360p"
        if self.button240.get_active(): self.bandwidth="240p"
        if self.bandwidth!=self.yt_dl.bandwidth:
          self.yt_dl.bandwidth=self.bandwidth
          self.yt_dl.restart()

    def on_aspect(self,widget):
        self.player.keep_aspect=not self.player.keep_aspect
        
    def on_search(self,widget):
        text = widget.get_text()
        if text:
            if text not in self.search_terms.keys():
                self.search_store.append([text])
                self.search_terms[text]=0
            else:
                self.search_terms[text]=self.search_terms[text]+1
        self.set_store(search=text,ordering=YT.orderings[0])
        self.iconView.grab_focus()
        
    def on_home(self, widget=None):
        self.yt_dl._url_cache=dict()
        self.reset_store()

    def on_dir(self, widget=None):
        ans=self.filechooser.run()
        if ans == 2:      
          self.download_directory=self.filechooser.get_filename()
          print self.download_directory
        self.filechooser.hide()
        
    def on_forward(self,widget=None):
        i=self.keys_for_stores.index(self.store['key'])
        if (i+1)>=len(self.keys_for_stores):
          return
        key=self.keys_for_stores[i+1]
        self.set_store(*key)

    def on_order(self,widget=None):
        search,ordering,playlist_id=self.store['key']
        if ordering=="": return
        new_ordering=YT.orderings[ (YT.orderings.index(ordering)+1)%len(YT.orderings)]
        self.set_store( search, new_ordering,playlist_id)
      
    def on_back(self,widget=None):
        i=self.keys_for_stores.index(self.store['key'])
        if (i-1)<0:
          return
        key=self.keys_for_stores[i-1]
        self.set_store(*key)
    
    def on_item_activated(self, widget, item):
        model = widget.get_model()
        title = model[item][COL_TITLE]
        print "click on:", title

        if model[item][COL_ITEM]['id']['kind']=="youtube#playlist":
          print "playlistID:",model[item][COL_ITEM]['id']['playlistId']
          self.set_store(playlist_id=model[item][COL_ITEM]['id']['playlistId'])        
        else:
          if self.playing:
             print "ignore"
             self.flash_cursor("red")
             return
          self.flash_cursor("green")
          self.playing=True
  
          url = model[item][COL_ITEM]['id']['videoId']
          print 'Playing ' + url
  
          t=threading.Thread(target=self.play, args=(url,title))
          t.daemon=True
          t.start()

    def on_play_playlist(self, widget=None):
        if self.playing or len(self.playlist['store'])==0:
           print "ignore"
           return
        self.playing=True
       
        print 'Playing playlist'

        t=threading.Thread(target=self.play_playlist, args=(self.playlist['store'],))
        t.daemon=True
        t.start()

    def playlist_message(self):
        if len(self.playlist['store'])==0:
          return "Playlist: empty"
        else:
          nitem=len(self.playlist['store'])
          time=0
          for item in self.playlist['store']:
            pass
#            time+=item[COL_ITEM]['duration']
          timestring=str(datetime.timedelta(seconds=time))
          return "Playlist: %i videos ["%nitem+timestring+"]"

    def on_list(self, widget=None):
        if self.iconView.get_model()!=self.playlist['store']:
          self.prev_key=self.store['key']
          self.set_store("__playlist__","")
        else:
          self.set_store(*self.prev_key)

    def get_item_video_url(self, item):
        print self.yt_dl.get_video_url( item['id']['videoId'])

    def set_playlist_label(self):
        self.playlistButton.set_label(str(len(self.playlist['store'])))

    def add_playlist_to_playlist(self,item):
        playlist_id=item['id']['playlistId']
        #~ self.flash_message("adding %i videos of "%item['size']+truncate(item['snippet']["title"],NSTRING-36)+" to playlist")
        self.flash_message("adding videos of "+truncate(item['snippet']["title"],NSTRING-36)+" to playlist")
        key=ytfeedkey(None,"relevance",playlist_id)
        store=self.fetch_and_cache(key)
        i=NPERPAGE
        while i<store['ntot']:
          i+=NPERPAGE
          self.expand_store_background(store)
        # fudge to allow some thumbnails to load:
        time.sleep(2)
        for row in store['store']:
          self.playlist['store'].append(row)
        self.set_playlist_label()


    def on_add(self,widget=None):
        model = self.iconView.get_model()
        if model!=self.playlist['store']:
          items=self.iconView.get_selected_items()
          if items:
            item=items[0]
            model = self.iconView.get_model()
            if model[item][COL_ITEM]['id']['kind']=="youtube#playlist":
              self.flash_cursor("blue")
              #~ gtk.idle_add(self.add_playlist_to_playlist,model[item][COL_ITEM])
              t=threading.Thread(target=self.add_playlist_to_playlist, args=(model[item][COL_ITEM],))
              t.daemon=True
              t.start()            
            else:
              row=model[item]
              self.playlist['store'].append(row)
              self.flash_message("added "+truncate(model[item][COL_TITLE],NSTRING-18)+" to playlist")
              self.flash_cursor("blue")
  
              t=threading.Thread(target=self.get_item_video_url, args=(row[COL_ITEM],))
              t.daemon=True
              t.start()
                       
        elif model==self.playlist['store']:
          if len(self.playlist_clipboard):
            items=self.iconView.get_selected_items()
            if items:
              item=items[0]
              row=model[item]
              self.playlist['store'].insert_before(model.get_iter(item),row=self.playlist_clipboard[0])
              self.playlist_clipboard.clear()
              self.flash_message("pasted "+truncate(model[item][COL_TITLE],NSTRING-18)+" in playlist")          
        self.set_playlist_label()

          
    def on_remove(self,widget=None):
        model = self.iconView.get_model()
        if model==self.playlist['store']:
          items=self.iconView.get_selected_items()
          if items:
            item=items[0]
            self.playlist_clipboard.clear()
            self.playlist_clipboard.append(model[item])
            self.playlist['store'].remove(model.get_iter(item))
            self.feed_mesg=self.playlist_message()
            self.update_mesg()
        self.set_playlist_label()

    def on_clear(self):
        self.playlist['store'].clear()
        self.set_playlist_label()
        self.feed_mesg=self.playlist_message()
        self.update_mesg()

    def on_download(self, widget=None):
         items=self.iconView.get_selected_items()
         if items:
           item=items[0]
           model = self.iconView.get_model()
           title = model[item][COL_TITLE]
           url = model[item][COL_ITEM]['id']['videoId']
           if url not in self.current_downloads:
             self.current_downloads.add(url)
             print 'downloading ' + url
             t=threading.Thread(target=self.download, args=(url,title),kwargs=dict(item=model[item][COL_ITEM]))
             t.daemon=True
             t.start()
         
    def download(self,url,title,item=None):
         progressbar=gtk.ProgressBar()
         progressbar.set_size_request(780,20)
         progressbar.modify_font(pango.FontDescription("sans 9"))
         progressbar.set_text(truncate("downloading " + title))
         self.vbox.pack_start(progressbar,False,False,0)
         progressbar.show()
         try:
           result,destination=self.yt_dl.download_video(url,self.download_directory,progressbar)
           self.message.set_text(truncate(result))
         except Exception as ex:
           print ex
           self.message.set_text("download "+truncate(title,NSTRING-16)+" failed")
         progressbar.destroy()
         self.current_downloads.remove(url)
         if item is not None:
           item["local_file"]=destination         

    def on_selection_changed(self, widget):
         items=widget.get_selected_items()
         if items:
           item=items[0]
           model = widget.get_model()
           self.message.set_text(truncate(model[item][COL_TOOLTIP]))
           infotxt="https://www.youtube.com/watch?v="+model[item][COL_ITEM]['id']['videoId']+"\n\n"+model[item][COL_ITEM]['snippet']['description']
           self.infoView.get_buffer().set_text(infotxt)

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

    def play(self,url,title):
        gobject.timeout_add(1000, self.busy_message,0,truncate("busy buffering "+title))
        mplayer_url=self.yt_dl.get_video_url(url)
        if mplayer_url.startswith("http"):
          self.player.play_url([mplayer_url])
          self.message.set_text(truncate("stopped playing "+title))
        else:
          self.message.set_text(truncate("failed to get url for "+title))
        self.playing=False
        gobject.timeout_add(2000, self.update_mesg)
        self.yt_dl.restart()

    def play_playlist(self,playlist):
        gobject.timeout_add(1000, self.busy_message,0,truncate("busy playing playlist"))
        urllist=[]
        for item in playlist:
          url=self.yt_dl.get_video_url( item[COL_ITEM]['id']['videoId'])
          if url.startswith("http"):
            urllist.append(url)
          else:
            self.message.set_text(truncate("failed to get url for "+item[COL_TITLE]))            
        if len(urllist):
          self.player.play_url(urllist)
          self.message.set_text(truncate("stopped playing playlist"))
        self.playing=False
        gobject.timeout_add(2000, self.update_mesg)
        self.yt_dl.restart()

    def on_save_playlist(self):

#        def f(buf,data=None):
#          data.append(buf)
#          return True
         
        data=[]
        for item in self.playlist['store']:
#          image=[]
#          item[1].save_to_callback(f,"png",user_data=image)
#          image=''.join(image)
          image=None
          data.append([item[0],image,item[2],item[3],item[4]])
        f=open("playlist","wb")
        cPickle.dump(data,f)
        f.close()
        
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
           self.iconView.scroll_to_path(items[0],True,0.,0.)
                    
    def on_player_select(self):
        p,v=AVAILABLE_VIDEO_PLAYERS.pop(0)
        AVAILABLE_VIDEO_PLAYERS.extend([(p,v)])
        self.player.player=p
        self.player.vo_driver=v
        self.yt_dl.use_http=True if p=='mplayer' else False
        self.flash_message("changed video player to: "+p+" with "+v)
    
    def on_yt_fetcher(self):
        if self.yt_dl.yt_fetcher=="pafy":
          self.yt_dl.yt_fetcher="youtube-dl"
        elif self.yt_dl.yt_fetcher=="youtube-dl":
          self.yt_dl.yt_fetcher="pafy"
        self.flash_message("changed youtube query to: "+self.yt_dl.yt_fetcher)
    
    def check_store_range(self):
        if len(self.store['store'])==self.store['ntot'] or self.store==self.playlist:
          return False
        cursor=self.iconView.get_cursor()
        if cursor:
          last=self.iconView.get_cursor()[0][0]+self.iconView.get_columns()        
          if last<MAX_STORE_SIZE and last>=len(self.store['store']):
            self.flash_message("** fetching data **")
            gtk.idle_add(self.expand_store_background,self.store)
            return True
              
    def on_key_press_event(self,widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
#        print "Key %s (%d) was pressed" % (keyname, event.keyval)
#        p=self.iconView.get_cursor()
#        print self.iconView.get_item_column(p[0]),self.iconView.get_item_row(p[0])
        if keyname in ["Up","Down"] and not self.iconView.is_focus():
          self.iconView.grab_focus()
          return True
        if keyname in ["Down"]:
          return self.check_store_range()
        if keyname in ["Page_Down"]:
          self.forwardButton.emit("activate")
        if keyname in ["Page_Up"]:
          self.backButton.emit("activate")
        if keyname in ["Escape"]:
          self.exitButton.emit("activate")          
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
        if keyname in ["Q","q"]:
          self.exitButton.emit("activate")
        if keyname in ["h","H"]:
          self.helpButton.emit("activate")
        if keyname in ["Alt_R","Alt_L"]:
          self.homeButton.emit("activate")
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
        if keyname in ["m","M"]:
          self.on_player_select()
        if keyname in ["y","Y"]:
          self.on_yt_fetcher()
        if keyname in ["l","L"]:
          self.playlistButton.emit("activate")
        if keyname in ["c","C"]:
          self.on_clear()
        if keyname in ["i","I"]:
          self.on_info()          
        if keyname in ["Z"]:
          self.default_key=self.store["key"]
          self.flash_message("setting starting screen")
#        if keyname in ["w","W"]:
#          self.on_save_playlist()          
        if keyname in ["2"]:
          self.button240.set_active(not self.button240.get_active())
        if keyname in ["3"]:
          self.button360.set_active(not self.button360.get_active())
        if keyname in ["4"]:
          self.button480.set_active(not self.button480.get_active())
#        if keyname in ["t","T"]:
#          self.buttontv.set_active(not self.buttontv.get_active())
          
    def on_quit(self, widget=None):
        self.cleanup(widget)
        gtk.main_quit()

    def cleanup(self,widget=None):
        search_terms=dict(sorted(self.search_terms.iteritems(), key=operator.itemgetter(1))[-100:])
        config=dict(download_directory=self.download_directory,
                          bandwidth=self.bandwidth,search_terms=search_terms,
                          default_key=self.default_key)      
        configuration_manager.write_config(config)
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
    result.add_option("-v", action="store", dest="player",
                      help="video player to use (mpv or mplayer)",default='mplayer')
    result.add_option("-d", action="store", dest="video_driver",
                      help="driver to use (eg xv, x11) ",default='xv')
    result.add_option("-y", action="store", dest="yt_fetcher",
                      help="youtube query to use (youtube-dl or pafy) ",default='youtube-dl')
    return result

if __name__=="__main__":
  (options, args) = new_option_parser().parse_args()  
  print options

  application=TheTube( fullscreen=options.fullscreen,preload_ytdl=options.preload_ytdl,
    vo_driver=options.video_driver,player=options.player,yt_fetcher=options.yt_fetcher)
  application.show_all()
  gtk.main()
