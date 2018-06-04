import kivy
import requests
import json
import webbrowser
import os
import threading, time
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.stacklayout import StackLayout
from kivy.uix.gridlayout import GridLayout
from kivy.utils import platform
from kivy.properties import StringProperty
from kivy.uix.popup import Popup

# Create both screens. Please note the root.manager.current: this is how
# you can control the ScreenManager from kv. Each screen has by default a
# property manager that gives you the instance of the ScreenManager used.

Builder.load_file('main.kv')

filename = "spot.txt"

if platform == 'linux':
    filename = '/home/pi/kivypi/spot.txt'

with open(filename) as f:
    lines = f.readlines()
#remove whitespace characters like `\n` at the end of each line
lines = [x.strip() for x in lines] 

sBasic = lines[0]
sRefreshToken = lines[1]
triggerToken = lines[2]

token = ''
playbackState = ''
currentVolume = '0'
running = 1

def refreshToken():
    global token
    r = requests.post("https://accounts.spotify.com/api/token", headers={'Authorization': sBasic}, data={'grant_type': 'refresh_token', 'refresh_token': sRefreshToken})
    print(r.status_code, r.reason)
    print(r.text[:300] + '...')
    token = 'Bearer ' + r.json()['access_token']

def setVolume(volume):
    r = requests.put("https://api.spotify.com/v1/me/player/volume?volume_percent=" + str(volume), headers={'Authorization': token})
    print(r.status_code, r.reason)
    print(r.text[:300] + '...')

def getVolume():
    try:
        global currentVolume
        r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
        device = r.json()['device']
        currentVolume = str(device['volume_percent'])
    except:
        print("Nothing Playing")
        return
    
refreshToken()
getVolume()

#Loop on seprate thread to refresh token
def mainThread():
    #check for playing status every so often?
    while running:
        for x in range(0, 600): 
            if (running):
                time.sleep( 1 )
        if (running == 0):
            break
        print ("Refreshing Token")
        refreshToken()

newthread = threading.Thread(target = mainThread)
newthread.start()

class MyPopup(Popup):
    def __init__(self,screen,**kwargs):
        super(MyPopup,self).__init__(**kwargs)
        self.screen = screen
    
    def closeandUpdate(self):
        self.screen.button_text = self.screen.button_text.split(".")[0]
        setVolume(self.screen.button_text)
        self.dismiss()


# Declare screens
class HomeScreen(Screen):
    button_text = StringProperty(currentVolume)
    def __init__(self,**kwargs):
        super(HomeScreen,self).__init__(**kwargs)
        self.popup = MyPopup(self)

    def btn_skip(self):
        def thread():
            #Skip 30s - add var to change the amount
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
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
            if(r.status_code == 401):
                refreshToken()
                return
            items = r.json()['item']
            #TrackId
            trackId = items['id']
            r = requests.get("https://api.spotify.com/v1/users/t7lfn4yveurkn8fa4hcvhf083/playlists/32AqjHtK9ofJcwuhWBot01", headers={'Authorization': token})
            #Check track is not already in playlist
            if trackId not in r.text: 
                print("Adding to Playlist")
                requests.post("https://api.spotify.com/v1/users/t7lfn4yveurkn8fa4hcvhf083/playlists/32AqjHtK9ofJcwuhWBot01/tracks?uris=spotify%3Atrack%3A" + trackId, headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()
        
    def btn_volDown(self):
        def thread():
            #Vol down
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            voldict = r.json()['device']
            volume = voldict['volume_percent']
            volume = int(volume) - 2
            r = requests.put("https://api.spotify.com/v1/me/player/volume?volume_percent=" + str(volume), headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_volUp(self):
        def thread():
            #Vol down
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            voldict = r.json()['device']
            volume = voldict['volume_percent']
            volume = int(volume) + 2
            r = requests.put("https://api.spotify.com/v1/me/player/volume?volume_percent=" + str(volume), headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_shuffle(self):
        def thread():
            #Shuffle
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            shuffleOn = r.json()['shuffle_state']
            shuffleOn = not shuffleOn
            r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=" + str(shuffleOn), headers={'Authorization': token})
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_previous(self):
        def thread():
                #Previous track (and play)
            r = requests.post("https://api.spotify.com/v1/me/player/previous", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_next(self):
        def thread():
            #Next track (and play)
            r = requests.post("https://api.spotify.com/v1/me/player/next", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_play(self):
        def thread():
            #Toggle Playback state
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            playing = r.json()['is_playing']
            if playing: 
                r = requests.put("https://api.spotify.com/v1/me/player/pause", headers={'Authorization': token})
                print(r.status_code, r.reason)
                print(r.text[:300] + '...')
            else:
                r = requests.put("https://api.spotify.com/v1/me/player/play", headers={'Authorization': token})
                print(r.status_code, r.reason)
                print(r.text[:300] + '...')

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_neilPlaylist(self):
        def thread():
            #Play Neil playlist
            payload = {'context_uri': 'spotify:user:t7lfn4yveurkn8fa4hcvhf083:playlist:1T6JGyXUm28pTaSJqH8ovz'}
            r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_rapFavsPlaylist(self):
        def thread():
            #Play rapFavs playlist
            payload = {'context_uri': 'spotify:user:t7lfn4yveurkn8fa4hcvhf083:playlist:2iYZUOSUmQasCPxaCVdLwD'}
            r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()
    
    def btn_musicBoizPlaylist(self):
        def thread():
            #Play musicBoiz playlist
            payload = {'context_uri': 'spotify:user:t7lfn4yveurkn8fa4hcvhf083:playlist:7909VP7zKBJohzWJKoRFx2'}
            r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.start()

    def btn_playLivingRoom(self):
        r = requests.post("https://www.triggercmd.com/api/ifttt?trigger=PlayLivRoom&computer=NBJ-DEV", data={'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjVhZjgyZGFkNWQyYjkzMDAxYmQ3OWJlYiIsImlhdCI6MTUyNjIxNDMxNH0.wdgJNc6ddItcHuiqWaTLaCXQ1QZyWgONL86YAuakM4I'})
        print(r.status_code, r.reason)
        print(r.text[:300] + '...')

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
            payload = {'context_uri': 'spotify:user:t7lfn4yveurkn8fa4hcvhf083:playlist:32AqjHtK9ofJcwuhWBot01'}
            r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')

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
            payload = {'context_uri': 'spotify:user:t7lfn4yveurkn8fa4hcvhf083:playlist:37i9dQZEVXcWS97182mQq0'}
            r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})    
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')

        newthread = threading.Thread(target = thread)
        newthread.start()
   
    def btn_tableTopPlaylist(self):
        def thread():
            #Play discoverWeekly playlist
            payload = {'context_uri': 'spotify:user:t7lfn4yveurkn8fa4hcvhf083:playlist:28uPKzcnErsq2OMG7EvqrG'}
            r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')

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

class PiDemoApp(App):

    def build(self):
        return sm

if __name__ == '__main__':
    PiDemoApp().run()