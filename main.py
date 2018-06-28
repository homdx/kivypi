from __future__ import print_function
import kivy
import requests
import json
import webbrowser
import os
import threading, time
import datetime
import socket
from random import sample
from string import ascii_lowercase
#from apiclient.discovery import build
#from httplib2 import Http
#from oauth2client import file, client, tools
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.slider import Slider
from kivy.uix.listview import ListItemButton
from kivy.utils import platform
from kivy.properties import StringProperty
from kivy.properties import ObjectProperty
from kivy.uix.popup import Popup
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.listview import ListView
from kivy.base import runTouchApp

os.chdir(os.path.dirname(__file__))
print("Current folder: " + os.getcwd())

root_widget = Builder.load_file('main.kv') 

filename = "spot.txt"

with open(filename) as f:
    lines = f.readlines()
#remove whitespace characters like `\n` at the end of each line
lines = [x.strip() for x in lines] 

sBasic = lines[0]
sRefreshToken = lines[1]
triggerToken = lines[2]

token = ''
playBackInfo = {"playing": False, "volume": '', "device": '', "deviceType": '', "shuffling": False, "currentSong": '', "currentArtist": '', "progress_ms": 0,"duration_ms": 0, "seekPos": 0}
devicesDict = {}
playlistDict = {}
running = 1

def refreshToken():
    global token
    r = requests.post("https://accounts.spotify.com/api/token", headers={'Authorization': sBasic}, data={'grant_type': 'refresh_token', 'refresh_token': sRefreshToken})
    print(r.status_code, r.reason)
    print(r.text[:300] + '...')
    token = 'Bearer ' + r.json()['access_token']

def getPlaybackData():
    try:
        global playBackInfo
        r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token, 'nocache': ''})
        deviceData = r.json()['device']
        item = r.json()['item']
        artist = item['artists']

        playing = r.json()['is_playing']
        volume = str(deviceData['volume_percent'])
        device = str(deviceData['name'])
        deviceType = str(deviceData['type'])
        shuffling = r.json()['shuffle_state']
        currentSong = str(item['name'])
        currentArtist = str(artist[0]['name'])
        progress_ms = r.json()['progress_ms']
        duration_ms = str(item['duration_ms'])
        seekPos = (float(r.json()['progress_ms']) / float(item['duration_ms']) * 100)

        playBackInfo = {"playing": playing, "volume": volume, "device": device, "deviceType": deviceType, "shuffling": shuffling, "currentSong": currentSong, "currentArtist": currentArtist, "progress_ms": progress_ms, "duration_ms": duration_ms, "seekPos": seekPos}
        print (playBackInfo)
    except Exception as e:
        print("Nothing Playing " + str(e.message))
        playBackInfo['playing'] = False
        playBackInfo['device'] = ''
        playBackInfo['deviceType'] = ''
        print (playBackInfo)

def setVolume(volume):
    try:
        global playBackInfo
        if (playBackInfo['deviceType'] == 'TV'):
            volume = int(volume) / 5
        print (volume)
        r = requests.put("https://api.spotify.com/v1/me/player/volume?volume_percent=" + str(volume), headers={'Authorization': token})
        playBackInfo['volume'] = str(volume)
        print(r.status_code, r.reason)
        print(r.text[:300] + '...')
    except:
        print("Nothing Playing")

def getUserInfo():
    try:
        global userId
        r = requests.get("https://api.spotify.com/v1/me", headers={'Authorization': token})
        print(r.status_code, r.reason)
        userId = r.json()['id']
        return userId
    except:
        print("Error getting user data")
        return

def getFavoritePlaylist():
    try:
        path = 'favoritePlaylist.txt'
        f=open(path, "r")
        fav = f.read()
        f.close
        return fav
    except:
        return 0

def getFavoriteDevice():
    try:
        path = 'favoriteDevice.txt'
        f=open(path, "r")
        fav = f.read()
        f.close
        return fav
    except:
        return 0

def getUserPlaylists():
    global playlistDict
    try:
        r = requests.get("https://api.spotify.com/v1/users/" + userId + "/playlists", headers={'Authorization': token})
        print(r.status_code, r.reason)
        items = r.json()['items']
        playlistDict = {}
        for item in items: 
            playlistDict[str(item['name'])] = str(item['id'])
        
        return playlistDict
    except:
        print("Error getting playlist data")
        return
        
def getUserDevices():
        global devicesDict
        r = requests.get("https://api.spotify.com/v1/me/player/devices", headers={'Authorization': token})
        devicesDict = {}
        devices = r.json()['devices']
        for device in devices:
            devicesDict[str(device['name'])] = str(device['id'])
    
def getGoogleCalanderItem():
        # Setup the Calendar API
        SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
        store = file.Storage('credentials.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('client_secrets.json', SCOPES)
            creds = tools.run_flow(flow, store)
        service = build('calendar', 'v3', http=creds.authorize(Http()))

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        #print('Getting the upcoming 10 events')
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                            maxResults=10, singleEvents=True,
                                            orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        calList = list()
        if not events:
            print('No upcoming events found.')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            calList.append(event['summary'] + " " + start)
            #print(start, event['summary'])
        return calList

def convertMs(millis):
    millis = int(millis)
    seconds=(millis/1000)%60
    seconds = int(seconds)
    minutes=(millis/(1000*60))%60
    minutes = int(minutes)

    return ("%d:%02d" % (minutes, seconds))
def updateLocalMedia(local_ms):
    global playBackInfo
    playBackInfo['progress_ms'] = int(local_ms)
    playBackInfo['seekPos'] = (float(local_ms) / float(playBackInfo['duration_ms']) * 100)
    #Currently hardcoded to Main screen, may need to pass the screen to update later
    try:
        sm.get_screen('home').update()
    except Exception as e:
        print ("No such screen: " + str(e.message))

refreshToken()
getPlaybackData()
userId = getUserInfo()
getUserPlaylists()
getUserDevices()
#calandarList = getGoogleCalanderItem()

#Loop on seprate thread to refresh token
def mainThread():
    while running:
        if (running == 0):
            break
        for x in range(0, 600): 
            if (running):
                time.sleep( 1 )
            else:
                break
            if x % 5 == 0:
                try:
                    getPlaybackData()
                    sm.get_screen('home').update()
                except Exception as e:
                    print ("No such screen")
                    
            if x % 20 == 0:
                getUserDevices()
        print ("Refreshing Token")
        refreshToken()
class VolumePopup(Popup):

    def __init__(self,screen,**kwargs):
        super(VolumePopup,self).__init__(**kwargs)
        self.screen = screen
        self.volume = playBackInfo['volume']
    
    def closeandUpdate(self):
        def thread():
            setVolume(self.screen.volume_buttonText)
        self.screen.volume_buttonText = self.screen.volume_buttonText.split(".")[0]
        newthread = threading.Thread(target = thread)
        newthread.start()
        self.dismiss()

    def exitandUpdate(self):
        def thread():
            self.screen.volume_buttonText = playBackInfo['volume']
        self.screen.volume_buttonText = self.screen.volume_buttonText.split(".")[0]
        newthread = threading.Thread(target = thread)
        newthread.start()
        self.dismiss()

    def btn_volDown(self):
        def thread():
            #Vol down*
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            try:
                voldict = r.json()['device']
                volume = voldict['volume_percent']
                volume = int(volume) - 1
                r = requests.put("https://api.spotify.com/v1/me/player/volume?volume_percent=" + str(volume), headers={'Authorization': token})
                global playBackInfo
                playBackInfo['volume'] = str(volume)
            except:
                print("Nothing Playing")
                return

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_volUp(self):
        def thread():
            #Vol down
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            try:
                voldict = r.json()['device']
                volume = voldict['volume_percent']
                volume = int(volume) + 1
                r = requests.put("https://api.spotify.com/v1/me/player/volume?volume_percent=" + str(volume), headers={'Authorization': token})
                global playBackInfo
                playBackInfo['volume'] = str(volume)
            except:
                print("Nothing Playing")
                return

        newthread = threading.Thread(target = thread)
        newthread.start()


# Declare screens
class HomeScreen(Screen):
    volume_buttonText = StringProperty(playBackInfo['volume'])
    song_buttonText = StringProperty(playBackInfo['currentSong'])
    artist_buttonText = StringProperty(playBackInfo['currentArtist'])
    device_buttonText = StringProperty(playBackInfo['device'])
    progress_buttonText = StringProperty(convertMs(playBackInfo['progress_ms']))
    seek_buttonText = StringProperty(str(playBackInfo['seekPos']))
    duration_buttonText = StringProperty(convertMs(playBackInfo['duration_ms']))
    shufflestate_buttonText = StringProperty(str(playBackInfo['shuffling']))

    def __init__(self,**kwargs): 
        super(HomeScreen,self).__init__(**kwargs)
        self.volPopup = VolumePopup(self)
        self.modifiedSlider = ModifiedSlider()
        self.modifiedSlider.bind(on_release=self.slider_release)
        self.updateProgess()

    def slider_release(self, location):
        def thread():
            try:
                test = float(location) / 100
                test = test * float(playBackInfo['duration_ms'])
                seek = int(test)
                requests.put("https://api.spotify.com/v1/me/player/seek?position_ms=" + str(seek), headers={'Authorization': token})
                #global playBackInfo
                #playBackInfo['seekPos'] = location
                updateLocalMedia(seek)
                #self.seek_buttonText = str(playBackInfo['seekPos'])
            except Exception as e:
                print("Nothing Playing " + e.message)
                return

        newthread = threading.Thread(target = thread)
        newthread.start()

    def updateProgess(self):
        def thread():
            while(running):
                if (running == 0):
                    print ("breaking")
                    break
                if(playBackInfo['playing'] == 1):
                    time.sleep( 1 )
                    increment = 999
                    if(playBackInfo['playing'] == 0):
                        #This can be refined later
                        print ("Paused after wait (presume that 500ms has passed)")
                        increment = 500
                    localProgess_ms = int(playBackInfo['progress_ms']) + increment
                    if (int(localProgess_ms) > int(playBackInfo['duration_ms'])):
                        print ("HERE")
                        localProgess_ms = localProgess_ms - int(playBackInfo['duration_ms'])
                        if (localProgess_ms < 0):
                            localProgess_ms = 0
                    updateLocalMedia(localProgess_ms)    
                    
        newthread = threading.Thread(target = thread)
        newthread.start()

    def update(self):
        def thread():
            self.volume_buttonText = str(playBackInfo['volume'])
            self.song_buttonText = str(playBackInfo['currentSong'])
            self.artist_buttonText = str(playBackInfo['currentArtist'])
            self.device_buttonText = str(playBackInfo['device'])
            self.progress_buttonText = convertMs(playBackInfo['progress_ms'])
            self.seek_buttonText = str(playBackInfo['seekPos'])
            self.duration_buttonText = convertMs(playBackInfo['duration_ms'])
            self.shufflestate_buttonText = str(playBackInfo['shuffling'])
        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_skip(self):
        def thread():
            #Skip 30s - add var to change the amount
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            try:
                progress_ms = r.json()['progress_ms']
                progress_ms += 30000
                r = requests.put("https://api.spotify.com/v1/me/player/seek?position_ms=" + str(progress_ms), headers={'Authorization': token})
                print(r.status_code, r.reason)
                print(r.text[:300] + '...')
                updateLocalMedia(progress_ms)
            except:
                print("Nothing Playing")
                return

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_addCurrentPlaying(self):
        def thread():
            favPlaylist = getFavoritePlaylist()
            print (favPlaylist)
            if (favPlaylist):
                r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
                try:
                    items = r.json()['item']
                    trackId = items['id']
                    r = requests.get("https://api.spotify.com/v1/users/" + userId + "/playlists/" + favPlaylist, headers={'Authorization': token})
                    #Check track is not already in playlist
                    if trackId not in r.text: 
                        print("Adding to Playlist")
                        requests.post("https://api.spotify.com/v1/users/" + userId + "/playlists/" + favPlaylist + "/tracks?uris=spotify%3Atrack%3A" + trackId, headers={'Authorization': token})
                except:
                    print("Error adding to playlist")
                    return       

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_shuffle(self):
        def thread():
            #Shuffle
            try:
                shuffleOn = playBackInfo['shuffling']
                shuffleOn = not shuffleOn
                r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=" + str(shuffleOn), headers={'Authorization': token})
                print(r.status_code, r.reason)
                print(r.text[:300] + '...')
                global playBackInfo
                playBackInfo['shuffling'] = shuffleOn
                self.shufflestate_buttonText = str(shuffleOn)
                #self.update()
            except:
                print("Nothing Playing")
                return

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_previous(self):
        def thread():
            #Previous track (and play)
            r = requests.post("https://api.spotify.com/v1/me/player/previous", headers={'Authorization': token})
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')
            updateLocalMedia(0)
            #getPlaybackData()
            #self.update()

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_next(self):
        def thread():
            #Next track (and play)
            r = requests.post("https://api.spotify.com/v1/me/player/next", headers={'Authorization': token})
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')
            updateLocalMedia(0)
            #getPlaybackData()
            #self.update()

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_play(self):
        def Play():
            r = requests.put("https://api.spotify.com/v1/me/player/play", headers={'Authorization': token})
            print(r.status_code, r.reason)
            global playBackInfo
            playBackInfo['playing'] = True
        def Pause():
            r = requests.put("https://api.spotify.com/v1/me/player/pause", headers={'Authorization': token})
            print(r.status_code, r.reason)
            global playBackInfo
            playBackInfo['playing'] = False
        def thread():
            #Toggle Playback state
            try:
                r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
                playing = r.json()['is_playing']
                if playing: 
                    Pause()
                else:
                    Play()
            except:
                print ("Nothing Playing trying to play on favorite device")
                payload = {'device_ids':[devicesDict[getFavoriteDevice()]]}
                r = requests.put("https://api.spotify.com/v1/me/player", json=payload, headers={'Authorization': token})
                print(r.status_code, r.reason)
                time.sleep( 1 )
                try:
                    r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
                    playing = r.json()['is_playing']
                    if playing: 
                        Pause()
                    else:
                        Play()
                except:
                    print ("No Devices")
                #self.update()
                return

        newthread = threading.Thread(target = thread)
        newthread.start()
        
    def btn_exit(self):
        global running
        running = 0
        App.get_running_app().stop()

    def btn_startCast(self):
        r = requests.post("https://www.triggercmd.com/api/ifttt?trigger=YTChromeCast2&computer=NickDesktop", data={'token': triggerToken})
        print(r.status_code, r.reason)
        print(r.text[:300] + '...')

    def btn_resumeCast(self):
        r = requests.post("https://www.triggercmd.com/api/ifttt?trigger=HandlePlayRequest&computer=NickDesktop", data={'token': triggerToken})
        print(r.status_code, r.reason)
        print(r.text[:300] + '...')

    def btn_pauseCast(self):
        r = requests.post("https://www.triggercmd.com/api/ifttt?trigger=HandlePauseRequest&computer=NickDesktop", data={'token': triggerToken})
        print(r.status_code, r.reason)
        print(r.text[:300] + '...')

    def btn_saveCast(self):
        r = requests.post("https://www.triggercmd.com/api/ifttt?trigger=HandleSaveRequest&computer=NickDesktop", data={'token': triggerToken})
        print(r.status_code, r.reason)
        print(r.text[:300] + '...')

    pass

class HomeScreen2(Screen):
    button_text = StringProperty()
    def __init__(self,**kwargs):
        super(HomeScreen2,self).__init__(**kwargs)
        self.volPopup = VolumePopup(self)
        self.button_text = self.btn_checkIP()

    def btn_exit(self):
        global running
        running = 0
        App.get_running_app().stop()

    def btn_checkIP(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip

    def btn_slack(self):
        #IFTTT Post to Slack
        r = requests.post("https://maker.ifttt.com/trigger/post_to_slack/with/key/UcYrm-X3zGUSSCqyH8UVl")
        print(r.status_code, r.reason)
        print(r.text[:300] + '...')

    def btn_lockPC(self):
        r = requests.post("https://www.triggercmd.com/api/ifttt?trigger=Lock&computer=NickDesktop", data={'token': triggerToken})
        print(r.status_code, r.reason)
        print(r.text[:300] + '...')

    def btn_trainTimetable(self):
        webbrowser.open('https://anytrip.com.au/stop/au2:206020')

    pass

class ModifiedSlider(Slider):
    def __init__(self, **kwargs):
        self.register_event_type('on_release')
        super(ModifiedSlider, self).__init__(**kwargs)

    def on_release(self):
        pass

    def on_touch_up(self, touch):
        super(ModifiedSlider, self).on_touch_up(touch)
        if touch.grab_current == self:
            self.dispatch('on_release')
            return True

class DevicesPage(BoxLayout):
    def __init__(self,screen,name,**kwargs):
        super(DevicesPage,self).__init__(**kwargs)
        self.rv.viewclass.screen = screen
        self.rv.viewclass.page = self
        self.name = name
        self.display.text = ''

    def populate(self, listDict):
        self.rv.data = [{'value': x} for x in listDict.keys()]

    def refresh(self):
        def thread():
            getUserDevices()
            self.populate(devicesDict)
        newthread = threading.Thread(target = thread)
        newthread.start()
        #WIP
    def device(self, name):
        def thread():
            print (self.display.text)
            devicepath = 'favoriteDevice.txt'
            if(self.display.text == 'Favorite'):
                try:
                    os.remove(devicepath)
                except:
                    print ("Adding New Favorite")
                f=open(devicepath, "a+")
                f.write(name)
                self.display.text = ''
                f.close
            else:
                payload = {'device_ids':[devicesDict[name]]}
                print(payload)
                r = requests.put("https://api.spotify.com/v1/me/player", json=payload, headers={'Authorization': token})
                print(r.status_code, r.reason)
                #Play on fav Playlist
                if (getFavoritePlaylist()):
                    time.sleep( 1 )
                    payload = {'context_uri': 'spotify:user:' + userId + ':playlist:' + getFavoritePlaylist()}
                    print (payload)
                    r = requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
                    print(r.status_code, r.reason)
                    time.sleep( 1 )
                    r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})
                    print(r.status_code, r.reason)

        newthread = threading.Thread(target = thread)
        newthread.start()

    pass

class PlaylistPage(BoxLayout):
    def __init__(self,screen,name,**kwargs):
        super(PlaylistPage,self).__init__(**kwargs)
        self.rv.viewclass.screen = screen
        self.rv.viewclass.page = self
        self.name = name
        self.entry = ''
        self.display.text = ''

    def populate(self, listDict):
        self.rv.data = [{'value': x} for x in listDict.keys()]

    def refresh(self):
        def thread():   
            getUserPlaylists()
            self.populate(playlistDict)
        newthread = threading.Thread(target = thread)
        newthread.start()

    def playlist(self, name):
        def thread():
            print (self.display.text)
            playlistPath = "favoritePlaylist.txt"
            if(self.display.text == 'Favorite'):
                try:
                    os.remove(playlistPath)
                except:
                    print ("Adding New Favorite")

                f=open(playlistPath, "a+")
                f.write(playlistDict[name])
                self.display.text = ''
                f.close
            else:
                if (playBackInfo['device'] == '' and getFavoriteDevice()):
                    payload = {'device_ids':[devicesDict[getFavoriteDevice()]]}
                    r = requests.put("https://api.spotify.com/v1/me/player", json=payload, headers={'Authorization': token})
                    print(r.status_code, r.reason)
                    time.sleep( 1 )
                payload = {'context_uri': 'spotify:user:' + userId + ':playlist:' + playlistDict[name]}
                requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
                time.sleep( 1 )
                requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()

    pass

class CalandarPage(BoxLayout):
    def __init__(self,screen,**kwargs):
        super(CalandarPage,self).__init__(**kwargs)
        self.rv.viewclass.screen = screen

    def populate(self, calList):
        self.rv.data = [{'value': x} for x in calList]

    pass

class CalandarScreen(Screen): 
    def __init__(self,**kwargs):
        super(CalandarScreen,self).__init__(**kwargs)
        self.calandarPage = CalandarPage(self)
        #self.calandarPage.populate(calandarList)
        self.add_widget(self.calandarPage)

    pass
class PlaylistScreen(Screen): 
    def __init__(self,**kwargs):
        super(PlaylistScreen,self).__init__(**kwargs)
        self.playListsPage = PlaylistPage(self, 'Playlists')
        self.playListsPage.populate(playlistDict)
        self.add_widget(self.playListsPage)
        self.playListsPage.entry = ''

    pass

class DevicesScreen(Screen): 
    def __init__(self,**kwargs):
        super(DevicesScreen,self).__init__(**kwargs)
        self.devicesPage = DevicesPage(self, 'Devices')
        self.devicesPage.populate(devicesDict)
        self.add_widget(self.devicesPage)

    pass

class LockScreen(Screen): 
    def btn_checkInput(self, input):
        print (input)
        if input == '4444':
            print('Correct')
            sm.current = 'home'
        self.display.text = ''

    pass

# Create the screen manager
print ("Before SM")
sm = ScreenManager()
print ("After SM")
sm.add_widget(LockScreen(name='lock'))
sm.add_widget(HomeScreen(name='home'))
sm.add_widget(HomeScreen2(name='home2'))
sm.add_widget(CalandarScreen(name='calandar'))
sm.add_widget(PlaylistScreen(name='playlists'))
sm.add_widget(DevicesScreen(name='devices'))

#Start thread after start
newthread = threading.Thread(target = mainThread)
newthread.start() 

class PiDemoApp(App):

    def build(self):
        return sm

if __name__ == '__main__':
    PiDemoApp().run()