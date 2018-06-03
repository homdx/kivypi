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

#readFile(filename)

# Create both screens. Please note the root.manager.current: this is how
# you can control the ScreenManager from kv. Each screen has by default a
# property manager that gives you the instance of the ScreenManager used.
Builder.load_file('main.kv')

filename = "spot.txt"

lines = [line.rstrip('\n') for line in open(filename)]
#print (lines)

print (lines[0])
for line in lines:
    line.replace('\r', '')
print (lines[0])

sBasic = lines[0]
print (sBasic)
sRefreshToken = lines[1]
triggerToken = lines[2]

if platform == 'linux':
    sBasic = sBasic[:-3]

r = requests.post("https://accounts.spotify.com/api/token", headers={'Authorization': sBasic}, data={'grant_type': 'refresh_token', 'refresh_token': sRefreshToken})
print(r.status_code, r.reason)
print(r.text[:300] + '...')
token = 'Bearer ' + r.json()['access_token']

def refreshToken():
    global token
    r = requests.post("https://accounts.spotify.com/api/token", headers={'Authorization': sBasic}, data={'grant_type': 'refresh_token', 'refresh_token': sRefreshToken})
    print(r.status_code, r.reason)
    print(r.text[:300] + '...')
    token = 'Bearer ' + r.json()['access_token']   

#refreshToken()

# Declare screens
class HomeScreen(Screen):

    def btn_skip(self):
        def thread():
            #Skip 30s - add var to change the amount
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
            if(r.status_code == 401):
                refreshToken()
                return
            progress_ms = r.json()['progress_ms']
            progress_ms += 30000
            r = requests.put("https://api.spotify.com/v1/me/player/seek?position_ms=" + str(progress_ms), headers={'Authorization': token})
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')

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
            #items = r.json()
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

    def btn_LockPC(self):
        r = requests.post("https://www.triggercmd.com/api/ifttt?trigger=Lock&computer=NickDesktop", data={'token': triggerToken})
        print(r.status_code, r.reason)
        print(r.text[:300] + '...')

    def btn_trainTimetable(self):
        webbrowser.open('https://anytrip.com.au/stop/au2:206020')
    pass

class HomeScreen2(Screen):

    def btn_exit(self):
        App.get_running_app().stop()

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

    pass

class LockScreen(Screen):
    def btn_checkInput(self, input):
        if input == '4444':
            print('test')
            sm.current = 'home'
        self.display.text = ''

    pass

# Create the screen manager
sm = ScreenManager()
sm.add_widget(LockScreen(name='lock'))
sm.add_widget(HomeScreen(name='home'))
sm.add_widget(HomeScreen2(name='home2'))

class TestApp(App):

    def build(self):
        return sm

if __name__ == '__main__':
    TestApp().run()