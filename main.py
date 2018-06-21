from __future__ import print_function
import kivy
import requests
import json
import webbrowser
import os
import threading, time
import datetime
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
print (os.path.dirname(__file__)) # relative directory path
print("Current folder: " + os.getcwd())

root_widget = Builder.load_file('main.kv') 

filename = "spot.txt"

if platform == 'linux':
    try:
        filename = '/home/pi/kivypi/spot.txt'
        import git
        git_dir = "/home/pi/kivypi"
        g = git.cmd.Git(git_dir)
        g.pull()
    except:
        print("unable to pull latest version")

with open(filename) as f:
    lines = f.readlines()
#remove whitespace characters like `\n` at the end of each line
lines = [x.strip() for x in lines] 

sBasic = lines[0]
sRefreshToken = lines[1]
triggerToken = lines[2]

token = ''
playBackInfo = {"playing": '', "volume": '', "device": '', "deviceType": '', "shuffling": ''}
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
        r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
        device = r.json()['device']

        playing = r.json()['is_playing']
        volume = str(device['volume_percent'])
        device = str(device['name'])
        #deviceType = device['type']
        #print (deviceType)
        shuffling = r.json()['shuffle_state']

        playBackInfo = {"playing": playing, "volume": volume, "device": device, "deviceType": device, "shuffling": shuffling}
        print (playBackInfo)
    except:
        print("Nothing Playing")

def setVolume(volume):
    try:
        global playBackInfo
        if (playBackInfo['deviceType'] == 'TV'):
            volume = int(volume) / 5
        print (volume)
        r = requests.put("https://api.spotify.com/v1/me/player/volume?volume_percent=" + str(volume), headers={'Authorization': token})
        playBackInfo['volume'] = volume
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

def getUserPlaylists():
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
            r = requests.get("https://api.spotify.com/v1/me/player/devices", headers={'Authorization': token})
            deviceDict = {}
            devices = r.json()['devices']
            for device in devices:
                deviceDict[str(device['name'])] = str(device['id'])

            return deviceDict
    
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
    
refreshToken()
#currentVolume = getVolume()
getPlaybackData()
userId = getUserInfo()
playlistDict = getUserPlaylists()
devicesDict = getUserDevices()
#calandarList = getGoogleCalanderItem()
print (playBackInfo)

#Loop on seprate thread to refresh token
def mainThread():
    #check for playing status every so often?
    while running:
        if (running == 0):
            break
        for x in range(0, 600): 
            if (running):
                time.sleep( 1 )
            else:
                break
            #if x % 20 == 0:
            #    getPlaybackData()
        print ("Refreshing Token")
        refreshToken()

newthread = threading.Thread(target = mainThread)
newthread.start() 

class VolumePopup(Popup):

    def __init__(self,screen,**kwargs):
        super(VolumePopup,self).__init__(**kwargs)
        self.screen = screen
        self.volume = playBackInfo['volume']
    
    def closeandUpdate(self):
        def thread():
            setVolume(self.screen.button_text)
        self.screen.button_text = self.screen.button_text.split(".")[0]
        newthread = threading.Thread(target = thread)
        newthread.start()
        self.dismiss()

    def exitandUpdate(self):
        def thread():
            self.screen.button_text = playBackInfo['volume']
        self.screen.button_text = self.screen.button_text.split(".")[0]
        newthread = threading.Thread(target = thread)
        newthread.start()
        self.dismiss()

    def btn_volDown(self):
        def thread():
            #Vol down
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            try:
                voldict = r.json()['device']
                volume = voldict['volume_percent']
                volume = int(volume) - 1
                r = requests.put("https://api.spotify.com/v1/me/player/volume?volume_percent=" + str(volume), headers={'Authorization': token})
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
                playBackInfo['volume'] = str(volume)
            except:
                print("Nothing Playing")
                return

        newthread = threading.Thread(target = thread)
        newthread.start()


# Declare screens
class HomeScreen(Screen):
    button_text = StringProperty(playBackInfo['volume'])
    def __init__(self,**kwargs):
        super(HomeScreen,self).__init__(**kwargs)
        self.volPopup = VolumePopup(self)

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
            except:
                print("Nothing Playing")
                return

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_addCurrentPlaying(self):
        def thread():
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            try:
                items = r.json()['item']
                trackId = items['id']
                r = requests.get("https://api.spotify.com/v1/users/" + userId + "/playlists/32AqjHtK9ofJcwuhWBot01", headers={'Authorization': token})
                #Check track is not already in playlist
                if trackId not in r.text: 
                    print("Adding to Playlist")
                    requests.post("https://api.spotify.com/v1/users/" + userId + "/playlists/32AqjHtK9ofJcwuhWBot01/tracks?uris=spotify%3Atrack%3A" + trackId, headers={'Authorization': token})
            except:
                print("Nothing Playing")
                return       

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_shuffle(self):
        def thread():
            #Shuffle
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            try:
                shuffleOn = r.json()['shuffle_state']
                shuffleOn = not shuffleOn
                r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=" + str(shuffleOn), headers={'Authorization': token})
                print(r.status_code, r.reason)
                print(r.text[:300] + '...')
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

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_next(self):
        def thread():
            #Next track (and play)
            r = requests.post("https://api.spotify.com/v1/me/player/next", headers={'Authorization': token})
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_play(self):
        def thread():
            #Toggle Playback state
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            try:
                playing = r.json()['is_playing']
                if playing: 
                    r = requests.put("https://api.spotify.com/v1/me/player/pause", headers={'Authorization': token})
                    print(r.status_code, r.reason)
                    print(r.text[:300] + '...')
                else:
                    r = requests.put("https://api.spotify.com/v1/me/player/play", headers={'Authorization': token})
                    print(r.status_code, r.reason)
                    print(r.text[:300] + '...')
            except:
                print("Nothing Playing")
                return

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_neilPlaylist(self):
        def thread():
            #Play Neil playlist
            payload = {'context_uri': 'spotify:user:' + userId + ':playlist:1T6JGyXUm28pTaSJqH8ovz'}
            requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
            time.sleep( 1 )
            requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_rapFavsPlaylist(self):
        def thread():
            #Play rapFavs playlist
            payload = {'context_uri': 'spotify:user:' + userId + ':playlist:2iYZUOSUmQasCPxaCVdLwD'}
            requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
            time.sleep( 1 )
            requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()
    
    def btn_musicBoizPlaylist(self):
        def thread():
            #Play musicBoiz playlist
            payload = {'context_uri': 'spotify:user:' + userId + ':playlist:7909VP7zKBJohzWJKoRFx2'}
            requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
            time.sleep( 1 )
            requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_playTV(self):
        def thread():
            r = requests.get("https://api.spotify.com/v1/me/player/devices", headers={'Authorization': token})
            devices = r.json()['devices']
            for device in devices:
                if device['name'] == 'TV':
                    id = device['id']
            try:
                payload = {'device_ids':[str(id)]}
                print(payload)
                r = requests.put("https://api.spotify.com/v1/me/player", json=payload, headers={'Authorization': token})
                print(r.status_code, r.reason)
                #Play on New Device
                time.sleep( 1 )
                payload = {'context_uri': 'spotify:user:' + userId + ':playlist:1T6JGyXUm28pTaSJqH8ovz'}
                r = requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
                print(r.status_code, r.reason)
                time.sleep( 1 )
                r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})
                print(r.status_code, r.reason)

            except:
                print("No device")
                return

        newthread = threading.Thread(target = thread)
        newthread.start()        

    def btn_playLivHome(self):
        def thread():
            r = requests.get("https://api.spotify.com/v1/me/player/devices", headers={'Authorization': token})
            devices = r.json()['devices']
            for device in devices:
                if device['name'] == 'Living Room Speaker':
                    id = device['id']
            try:
                payload = {'device_ids':[str(id)]}
                print(payload)
                r = requests.put("https://api.spotify.com/v1/me/player", json=payload, headers={'Authorization': token})
                print(r.status_code, r.reason)
                #Play on New Device
                time.sleep( 1 )
                payload = {'context_uri': 'spotify:user:' + userId + ':playlist:1T6JGyXUm28pTaSJqH8ovz'}
                r = requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
                print(r.status_code, r.reason)
                time.sleep( 1 )
                r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})
                print(r.status_code, r.reason)
            except:
                print("No device")
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

    def btn_considerPlaylist(self):
        def thread():
            #Play consider playlist
            payload = {'context_uri': 'spotify:user:' + userId + ':playlist:32AqjHtK9ofJcwuhWBot01'}
            requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
            time.sleep( 1 )
            requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_trainTimetable(self):
        webbrowser.open('https://anytrip.com.au/stop/au2:206020')
    pass

class HomeScreen2(Screen):

    def btn_exit(self):
        global running
        running = 0
        App.get_running_app().stop()

    def btn_discoverWeeklyPlaylist(self):
        def thread():
            #Play discoverWeekly playlist
            payload = {'context_uri': 'spotify:user:' + userId + ':playlist:37i9dQZEVXcWS97182mQq0'}
            r = requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})  
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')  
            time.sleep( 1 )
            r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')  

        newthread = threading.Thread(target = thread)
        newthread.start()
   
    def btn_tableTopPlaylist(self):
        def thread():
            #Play discoverWeekly playlist
            payload = {'context_uri': 'spotify:user:' + userId + ':playlist:28uPKzcnErsq2OMG7EvqrG'}
            requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
            time.sleep( 1 )
            requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_slack(self):
        #IFTTT Post to Slack
        r = requests.post("https://maker.ifttt.com/trigger/post_to_slack/with/key/UcYrm-X3zGUSSCqyH8UVl")
        print(r.status_code, r.reason)
        print(r.text[:300] + '...')

    def btn_lockPC(self):
        r = requests.post("https://www.triggercmd.com/api/ifttt?trigger=Lock&computer=NickDesktop", data={'token': triggerToken})
        print(r.status_code, r.reason)
        print(r.text[:300] + '...')

    pass

class DevicesPage(BoxLayout):
    def __init__(self,screen,name,**kwargs):
        super(DevicesPage,self).__init__(**kwargs)
        self.rv.viewclass.screen = screen
        self.name = name

    def populate(self, listDict):
        self.rv.data = [{'value': x} for x in listDict.keys()]

    pass

class PlaylistPage(BoxLayout):
    def __init__(self,screen,name,**kwargs):
        super(PlaylistPage,self).__init__(**kwargs)
        self.rv.viewclass.screen = screen
        self.name = name

    def populate(self, listDict):
        self.rv.data = [{'value': x} for x in listDict.keys()]

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

    def playlist(self, name):
        def thread():
            payload = {'context_uri': 'spotify:user:' + userId + ':playlist:' + playlistDict[name]}
            requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
            time.sleep( 1 )
            requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()

    pass

class DevicesScreen(Screen): 
    def __init__(self,**kwargs):
        super(DevicesScreen,self).__init__(**kwargs)
        self.devicesPage = DevicesPage(self, 'Devices')
        self.devicesPage.populate(devicesDict)
        self.add_widget(self.devicesPage)

    #WIP
    def device(self, id):
        def thread():
            payload = {'device_ids':[devicesDict[id]]}
            print(payload)
            r = requests.put("https://api.spotify.com/v1/me/player", json=payload, headers={'Authorization': token})
            print(r.status_code, r.reason)
            #Play on New Device
            #time.sleep( 1 )
            #payload = {'context_uri': 'spotify:user:' + userId + ':playlist:1T6JGyXUm28pTaSJqH8ovz'}
            #r = requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
            #print(r.status_code, r.reason)
            #time.sleep( 1 )
            #r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})
            #print(r.status_code, r.reason)

        newthread = threading.Thread(target = thread)
        newthread.start()

    pass

class LockScreen(Screen): 
    def btn_checkInput(self, input):
        if input == '4444':
            print('Correct')
            sm.current = 'home'
        self.display.text = ''

    pass

# Create the screen manager
sm = ScreenManager()
sm.add_widget(LockScreen(name='lock'))
sm.add_widget(HomeScreen(name='home'))
sm.add_widget(HomeScreen2(name='home2'))
sm.add_widget(CalandarScreen(name='calandar'))
sm.add_widget(PlaylistScreen(name='playlists'))
sm.add_widget(DevicesScreen(name='devices'))
class PiDemoApp(App):

    def build(self):
        return sm

if __name__ == '__main__':
    PiDemoApp().run()