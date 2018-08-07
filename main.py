from __future__ import print_function
import kivy
import requests
import json
import webbrowser
import os
import platform as osplatform
import threading, time
import datetime
import socket
import pychromecast
import signal
import argparse
import kivy.utils as utils
import tokenHandler
from threading import Event
from pychromecast.controllers.youtube import YouTubeController
from random import sample
from string import ascii_lowercase
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
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.base import runTouchApp

os.chdir(os.path.dirname(__file__))
print("Current folder: " + os.getcwd())

WINDOWS = (osplatform.system() == "Windows")
LINUX = (osplatform.system() == "Linux")
MAC = (osplatform.system() == "Darwin")

if not LINUX:
    import browser

root_widget = Builder.load_file('main.kv') 

sBasic = None
sAccessToken = None
sRefreshToken = None
triggerToken = None

running = 1
token = ''
devicesDict = {}
playlistDict = {}

#stores data for currently packback data from Spotify
playBackInfo = {"playing": False, "volume": '', "device": '', "deviceType": '', "shuffling": False, "currentSong": '', "currentArtist": '', "progress_ms": 0,"duration_ms": 0, "seekPos": 0}

#Refresh spotfy token

def readTokenData():
    try:
        global sBasic
        global sAccessToken
        global sRefreshToken
        global triggerToken
        global token

        if not os.path.isfile('tokenData.json'):
            print ('No existing token data')
            return

        with open('tokenData.json') as tokenData:
            data = json.load(tokenData)
            if('sBasic' in data):
                sBasic = data['sBasic']
            if('sAccessToken' in data):
                sAccessToken = data['sAccessToken']
            if('sRefreshToken' in data):
                sRefreshToken = data['sRefreshToken']
            if('triggerToken' in data):
                triggerToken = data['triggerToken']

    except Exception as e:
        print ('Error reading token data:' + e.message)

#update the dictionary with latest data from spotify if anything is playing
def getPlaybackData():
    def thread():
        try:
            global playBackInfo
            global token
            r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token, 'nocache': ''})
            if (r.status_code == 204):
                playBackInfo = {"playing": False, "volume": '0', "device": '', "deviceType": '', "shuffling": False, "currentSong": '', "currentArtist": '', "progress_ms": 0, "duration_ms": 0, "seekPos": 0}
                return
            if (r.status_code == 401):
                token = ''
                playBackInfo = {"playing": False, "volume": '0', "device": '', "deviceType": '', "shuffling": False, "currentSong": '', "currentArtist": '', "progress_ms": 0, "duration_ms": 0, "seekPos": 0}
                return
            volume = ''
            device = ''
            deviceType = ''
            currentSong = ''
            duration_ms = 0
            artist = ''
            currentArtist = ''
            playing = False
            shuffling = False
            progress_ms = 0
            seekPos = 0
            
            if ('device' in r.json()):
                deviceData = r.json()['device']
                volume = str(deviceData['volume_percent'])
                device = str(deviceData['name'])
                deviceType = str(deviceData['type'])
                
            if ('item' in r.json() and r.json()['item'] != None):
                item = r.json()['item']
                currentSong = str(item['name'])
                duration_ms = str(item['duration_ms'])
                artist = item['artists']
                currentArtist = str(artist[0]['name'])
            try:
                playing = r.json()['is_playing']
                shuffling = r.json()['shuffle_state']
                progress_ms = r.json()['progress_ms']
                if ('item' in r.json() and r.json()['item'] != None):
                    seekPos = (float(progress_ms) / float(item['duration_ms']) * 100)
            except:
                print ('Error')

            playBackInfo = {"playing": playing, "volume": volume, "device": device, "deviceType": deviceType, "shuffling": shuffling, "currentSong": currentSong, "currentArtist": currentArtist, "progress_ms": progress_ms, "duration_ms": duration_ms, "seekPos": seekPos}
            try:
                print (playBackInfo)
            except:
                print ('Cant print playback')
        except Exception as e:
            print("Nothing Playing:")
            try:
                print(e.message)
            except:
                print('Unhandled error')
            playBackInfo = {"playing": False, "volume": '0', "device": '', "deviceType": '', "shuffling": False, "currentSong": '', "currentArtist": '', "progress_ms": 0, "duration_ms": 0, "seekPos": 0}
            #print (playBackInfo)
    newthread = threading.Thread(target = thread)
    newthread.daemon = True
    newthread.start()

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

#get user info for Spotify account
def getUserInfo():
    try:
        global userId
        global userDisplayName
        r = requests.get("https://api.spotify.com/v1/me", headers={'Authorization': token})
        print(r.status_code, r.reason)
        userId = r.json()['id']
        userDisplayName = r.json()['display_name']
        return userId
    except:
        print("Error getting user data")
        return

#Load user's prefs based on input
def getUserPrefs(prefData):
    prefsFilename = "prefs.json"
    if not os.path.isfile(prefsFilename):
        print ('No existing user pref data')
        return False

    with open(prefsFilename) as jsonData:
        data = json.load(jsonData)
        if(prefData in data):
            return data[prefData]
        else:
            return False

#Set user prefs based on pref type and input:
def setUserPrefs(prefType, prefData):
    prefsFilename = "prefs.json"
    if (type(prefType) is not unicode):
        prefType = unicode(prefType, "utf-8")
    if (type(prefData) is not unicode):
        prefData = unicode(prefData, "utf-8")
    if (os.path.isfile(prefsFilename) and os.stat(prefsFilename).st_size != 0):
        jsonFile = open(prefsFilename, "r") # Open the JSON file for reading
        data = json.load(jsonFile) # Read the JSON into the buffer
        jsonFile.close() # Close the JSON file
        data[prefType] = prefData
    else:
        jsonFile = open(prefsFilename, "a+") # Create the JSON file
        data = {prefType: prefData}
        jsonFile.write(json.dumps(data))
        jsonFile.close() # Close the JSON file
        return

    ## Save our changes to JSON file
    jsonFile = open(prefsFilename, "w+")
    jsonFile.write(json.dumps(data))
    jsonFile.close()

#~~~~~~~~~~~~~~~~~~~~~~

#Get current Spotify users playlists 
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
        print("Unable to get playlist data")
        return
        
#Get current Spotify users devices   
def getUserDevices():
    def thread():
        try:
            global devicesDict
            r = requests.get("https://api.spotify.com/v1/me/player/devices", headers={'Authorization': token})
            devicesDict = {}
            devices = r.json()['devices']
            for device in devices:
                devicesDict[str(device['name'])] = str(device['id'])
        except:
            print ('Unable to get Devices')

    newthread = threading.Thread(target = thread)
    newthread.daemon = True
    newthread.start()
        
#convert MS input into a current time (minutes & seconds) e.g. 0:25
def convertMs(millis):
    millis = int(millis)
    seconds=(millis/1000)%60
    seconds = int(seconds)
    minutes=(millis/(1000*60))%60
    minutes = int(minutes)

    return ("%d:%02d" % (minutes, seconds))

#updates the frontend display with the expected progress of music playback
def updateLocalMedia(local_ms):
    global playBackInfo
    playBackInfo['progress_ms'] = int(local_ms)
    try:
        playBackInfo['seekPos'] = (float(local_ms) / float(playBackInfo['duration_ms']) * 100)
    except ZeroDivisionError:
        playBackInfo['seekPos'] = 0
    #Currently hardcoded to Main screen, may need to pass the screen to update later
    try:
        sm.get_screen('home').update()
    except Exception as e:
        print ("No such screen: " + str(e.message))

def find_from( s, start):
    return s.split(start,1)[1].rstrip()

def find_previous( s, start):
    return s.split(start,1)[0].rstrip()

def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

#Shows the provided alert message to user
def alert(message):
    #popup = Popup(content=Label(text=message), size_hint=(None, None), size=(400, 400))
    content = Button(text=message)
    #content.add_widget(Label(text=message))
    popup = Popup(title='Alert', content=content, size_hint=(None, None), size=(500, 500))

    # bind the on_press event of the button to the dismiss function
    content.bind(on_press=popup.dismiss)
    popup.open()

def checkMessages(mtype):
    try:
        if os.path.isfile(mtype + '.txt'):
            os.remove(mtype + '.txt') 
            return True
    except:
        return False

#Get initial spotify data (should be moved to function after multi user support)
def getSpotifyData():
    #refreshToken()
    getPlaybackData()
    getUserInfo()
    getUserPlaylists()
    getUserDevices()

def refreshToken():
    try:
        global token
        if (sRefreshToken):
            r = requests.post("http://13.75.194.36:8080/refresh_token", data={'refresh_token': sRefreshToken})
        else:
            print ('No refresh token')
            return
        if 'access_token' in r.json():
            token = r.json()['token_type'] + ' ' + r.json()['access_token']
    except Exception as e:
        print (e.message)
        return

def newUserToken():
    def startHandler():
        tokenHandler.run()
    newthread = threading.Thread(target = startHandler)
    newthread.daemon = True
    newthread.start()
    if LINUX:
        webbrowser.open('http://13.75.194.36:8080/login')
    else:
        #run from cefpython if not Linux
        browser.run()

def initToken(link):
    readTokenData()
    refreshToken()
    if (token is not ''):
        getSpotifyData()
        if link:
            alert('Linked Spotify Account: ' + userDisplayName)

#Initialize token data 0 being that we are not linking a new account
initToken(0)

#Loop on seprate thread to refresh token every 600 seconds and update Local progress of music playback
def mainThread():
    while running:
        if (running == 0):
            break
        if (sRefreshToken is None):
            if (checkMessages('newtoken')):
                initToken(1)
                continue
            time.sleep( 1 )
            continue
        for x in range(0, 600): 
            if (running):
                if (checkMessages('newtoken')):
                    initToken(1)
                    continue
                time.sleep( 1 )
                try:
                    sm.get_screen('home').updateProgess()
                except:
                    print ("No such screen / error updating progress")
            else:
                break
            if x % 10 == 0:
                try:
                    getPlaybackData()
                    sm.get_screen('home').update()
                except Exception as e:
                    print ("No such screen / error updating screen")
                    print (e.message)
                    
            if x % 20 == 0:
                getUserDevices()
        print ("Refreshing Token")
        refreshToken()

# Main screen
class HomeScreen(Screen):
    volume_buttonText = StringProperty(playBackInfo['volume'])
    song_buttonText = StringProperty(playBackInfo['currentSong'])
    artist_buttonText = StringProperty(playBackInfo['currentArtist'])
    device_buttonText = StringProperty(playBackInfo['device'])
    progress_buttonText = StringProperty(convertMs(playBackInfo['progress_ms']))
    seek_buttonText = StringProperty(str(playBackInfo['seekPos']))
    duration_buttonText = StringProperty(convertMs(playBackInfo['duration_ms']))
    shufflestate_buttonText = StringProperty(str(playBackInfo['shuffling']))
    color = StringProperty(kivy.utils.get_color_from_hex('#FFFFF'))

    def __init__(self,**kwargs): 
        super(HomeScreen,self).__init__(**kwargs)
        self.volPopup = VolumePopup(self)
        self.modifiedSlider = ModifiedSlider()
        self.modifiedSlider.bind(on_release=self.slider_release)

    def slider_release(self, location):
        def thread():
            try:
                seekPos = float(location) / 100
                seekPos = seekPos * float(playBackInfo['duration_ms'])
                seek = int(seekPos)
                requests.put("https://api.spotify.com/v1/me/player/seek?position_ms=" + str(seek), headers={'Authorization': token})
                updateLocalMedia(seek)
            except Exception as e:
                print("Nothing Playing " + e.message)
                return

        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()

    def updateProgess(self):
        if(playBackInfo['playing'] == 1):
            increment = 999
            if(playBackInfo['playing'] == 0):
                #This can be refined later
                print ("Paused after wait (presume that 500ms has passed)")
                increment = 500
            localProgess_ms = int(playBackInfo['progress_ms']) + increment
            if (int(localProgess_ms) > int(playBackInfo['duration_ms'])):
                localProgess_ms = localProgess_ms - int(playBackInfo['duration_ms'])
                if (localProgess_ms < 0):
                    localProgess_ms = 0
            updateLocalMedia(localProgess_ms)

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
        newthread.daemon = True
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
        newthread.daemon = True
        newthread.start()

    def btn_addCurrentPlaying(self):
        def thread():
            favPlaylist = getUserPrefs('favoritePlaylist')
            if (favPlaylist):
                r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
                try:
                    if( r.status_code == 204 or r.json()['item'] == None):
                        print ("Nothing playing")   
                        return
                    items = r.json()['item']
                    trackId = items['id']
                    r = requests.get("https://api.spotify.com/v1/users/" + userId + "/playlists/" + favPlaylist, headers={'Authorization': token})
                    #Check track is not already in playlist
                    if trackId not in r.text: 
                        p = requests.post("https://api.spotify.com/v1/users/" + userId + "/playlists/" + favPlaylist + "/tracks?uris=spotify%3Atrack%3A" + trackId, headers={'Authorization': token})
                        if (p.status_code < 400):
                            print("Added to Playlist")
                    else:
                        alert('Already in Favorite Playlist')
                except:
                    print("Error adding to playlist")
                    return       

        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()

    #Need to add to users selected 'Reconsider' Playlist, then remove from Favorite Playlist
    #Negative (Current song not in favorite) - just add to Reconsider?
    def btn_moveCurrentPlaying(self):
        def thread():
            backPlaylist = getUserPrefs('favoriteBackupPlaylist')
            favPlaylist = getUserPrefs('favoritePlaylist')
            if (backPlaylist and favPlaylist):
                r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
                try:
                    if( r.status_code == 204 or r.json()['item'] == None):
                        alert("Nothing playing")   
                        return
                    items = r.json()['item']
                    trackId = items['id']
                    payload = { "tracks": [{ "uri": "spotify:track:" + trackId }]}
                    r = requests.get("https://api.spotify.com/v1/users/" + userId + "/playlists/" + favPlaylist, headers={'Authorization': token})
                    #Check track is not already in playlist
                    if trackId in r.text: 
                        #payload required for delete endpoint but not post
                        p = requests.delete("https://api.spotify.com/v1/users/" + userId + "/playlists/" + favPlaylist + "/tracks", json=payload, headers={'Authorization': token})
                        if (p.status_code < 400):
                            print("Removed from Favorite Playlist")
                    else:
                        alert('Track not in Favorite Playlist')
                        return

                    r = requests.get("https://api.spotify.com/v1/users/" + userId + "/playlists/" + backPlaylist, headers={'Authorization': token})
                    if trackId not in r.text:
                        p = requests.post("https://api.spotify.com/v1/users/" + userId + "/playlists/" + backPlaylist + "/tracks?uris=spotify%3Atrack%3A" + trackId, headers={'Authorization': token})
                        if (p.status_code < 400):
                            print("Added to Backup Playlist")
                    
                except:
                    alert("Error adding to playlist")
                    return
            else:
                alert('You need a Favorite and Backup playlist to do this')   

        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()

    def btn_shuffle(self):
        def thread():
            #Shuffle
            try:
                global playBackInfo
                shuffleOn = playBackInfo['shuffling']
                shuffleOn = not shuffleOn
                r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=" + str(shuffleOn), headers={'Authorization': token})
                if (r.status_code is not 204):
                    return
                playBackInfo['shuffling'] = shuffleOn
                self.shufflestate_buttonText = str(shuffleOn)
            except:
                print("Nothing Playing")
                return

        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()

    def btn_previous(self):
        def thread():
            #Previous track (and play)
            r = requests.post("https://api.spotify.com/v1/me/player/previous", headers={'Authorization': token})
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')
            updateLocalMedia(0)
            #getPlaybackData()

        newthread = threading.Thread(target = thread)
        newthread.daemon = True
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
        newthread.daemon = True
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
                if (r.status_code == 204 and getUserPrefs('favoriteDevice')):
                    payload = {'device_ids':[devicesDict[getUserPrefs('favoriteDevice')]]}
                    r = requests.put("https://api.spotify.com/v1/me/player", json=payload, headers={'Authorization': token})
                    print(r.status_code, r.reason)
                    time.sleep( 1 )
                    r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
                    playing = r.json()['is_playing']
                    return
                else:
                    if (r.status_code == 400):
                        alert('Bad request: ' + r.json()['error']['message'])
                        return
                    if ('is_playing' in r.json()):
                        playing = r.json()['is_playing']
                    else:
                        return
                if playing: 
                    Pause()
                else:
                    Play()
            except KeyError as e:
                alert('Unable to play on favorite device: ' + e.message)
            except Exception as e:
                alert("Error playing or no favorite device: " + e.message)


        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()
        
    def btn_exit(self):
        global running
        running = 0
        App.get_running_app().stop()

    def btn_startCast_OLD(self):
        r = requests.post("https://www.triggercmd.com/api/ifttt?trigger=YTChromeCast2&computer=NickDesktop", data={'token': triggerToken})
        print(r.status_code, r.reason)
        print(r.text[:300] + '...')

    def btn_startCast(self, rType):

        def thread():

            def checkLast(last, x, num):
                if(last == ''):
                    print ('error: ' + x + " :" + str(num))

            def f(x):
                return {
                'month': "https://www.reddit.com/r/YoutubeHaiku/top.json?sort=top&t=month&limit=100",
                'week': "https://www.reddit.com/r/YoutubeHaiku/top.json?sort=top&t=week&limit=100",
                'day': "https://www.reddit.com/r/YoutubeHaiku/top.json?sort=top&t=day&limit=100"
                }.get(x, "https://www.reddit.com/r/YoutubeHaiku/top.json?sort=top&t=day&limit=100") 

            if(not getUserPrefs('favoriteCastDevice')):
                alert('Select a default Cast device in settings')
                return

            request = f(rType)

            print (request)

            thislist = []
                    
            r = requests.get(request, headers={'cache-control': 'no-cache', 'user-agent': 'PostmanRuntime/7.1.5'})
            #print (r.code)
            if ('message' in r.json()):
                print (r.json()['message'])
            data2 = r.json()['data']
            children = data2['children']
            for c in children:
                innerData = c['data']
                x = innerData['url']
                x = x.replace('%26', '&')
                x = x.replace('%3D', '=')
                if ('?start' in x):
                    print ('Skipping vid: ' + x)
                    continue
                elif ('attribution_link' in x):
                    thislist.append(find_between(x, 'v=', '&'))
                    checkLast(thislist[-1], x, 1)
                    continue
                elif('?t=' in x):
                    thislist.append(find_between(x, 'be/', '?'))
                    checkLast(thislist[-1], x, 3)
                    continue
                elif ('&' in x):
                    thislist.append(find_between(x, 'v=', '&'))
                    checkLast(thislist[-1], x, 2)
                    continue
                elif('be/' in x):
                    thislist.append(find_from(x, 'be/'))
                    checkLast(thislist[-1], x, 4)
                    continue
                elif('v=' in x):
                    thislist.append(find_from(x, 'v='))
                    checkLast(thislist[-1], x, 5)
                    continue
                else:
                    print("Invalid url: " + x)

            # Triggers program exit
            shutdown = Event()

            def signal_handler(x,y):
                shutdown.set()

            chromecasts = pychromecast.get_chromecasts()
            print([cc.device.friendly_name for cc in chromecasts])

            if(len(chromecasts) == 0):
                alert('No cast devices found')
                return

            if(getUserPrefs('favoriteCastDevice') not in [cc.device.friendly_name for cc in chromecasts]):
                alert('Favorite device ' + getUserPrefs('favoriteCastDevice') + '  not Available')
                return

            cast = next(cc for cc in chromecasts if cc.device.friendly_name == getUserPrefs('favoriteCastDevice'))
            # Wait for cast device to be ready
            cast.wait()
            mc = cast.media_controller

            # Create and register a YouTube controller
            yt = YouTubeController()
            cast.register_handler(yt)

            # Play the video ID we've been given
            yt.play_video(thislist[0])
            thislist.remove(thislist[0])

            for x in thislist:
                yt.add_to_queue(x)

        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()

    def btn_startCastAll(self):

        def thread():
            filename = "YTTopWeek_All.txt"

            if(not getUserPrefs('favoriteCastDevice')):
                alert('Select a default Cast device in settings')
                return

            with open(filename) as f:
                lines = f.readlines()

            urlDict = {}
            for x in lines:
                try:
                    urlDict[find_from(x,',')] = int(find_previous(x,','))
                except:
                    print('invalid')

            sorted_x = sorted(urlDict.items(), reverse=True,  key=lambda x: x[1])
            thislist = []

            for x in sorted_x:
                if ('&' in x[0]):
                    thislist.append(find_between(x[0], 'v=', '&'))
                elif('be/' in x[0]):
                    thislist.append(find_from(x[0], 'be/'))
                elif('v=' in x[0]):
                    thislist.append(find_from(x[0], 'v='))
                else:
                    print("Invalid url: " + x)

            print (str(thislist))

            # Triggers program exit
            shutdown = Event()

            def signal_handler(x,y):
                shutdown.set()

            chromecasts = pychromecast.get_chromecasts()
            print([cc.device.friendly_name for cc in chromecasts])

            if(len(chromecasts) == 0):
                alert('No cast devices found')
                return

            if(getUserPrefs('favoriteCastDevice') not in [cc.device.friendly_name for cc in chromecasts]):
                alert('Favorite device ' + getUserPrefs('favoriteCastDevice') + '  not Available')
                return

            cast = next(cc for cc in chromecasts if cc.device.friendly_name == "Chromecast")
            # Wait for cast device to be ready
            cast.wait()
            mc = cast.media_controller

            # Initialize a connection to the Chromecast

            # Create and register a YouTube controller
            yt = YouTubeController()
            cast.register_handler(yt)

            # Play the video ID we've been given
            yt.play_video(thislist[0])
            thislist.remove(thislist[0])

            for x in thislist:
                yt.add_to_queue(x)

        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()

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
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return 'Cant Connect'

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

    def btn_refresh(self):
        refreshToken()

    pass

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
        newthread.daemon = True
        newthread.start()
        self.dismiss()

    def exitandUpdate(self):
        def thread():
            self.screen.volume_buttonText = playBackInfo['volume']
        self.screen.volume_buttonText = self.screen.volume_buttonText.split(".")[0]
        newthread = threading.Thread(target = thread)
        newthread.daemon = True
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
        newthread.daemon = True
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
        newthread.daemon = True
        newthread.start()

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
        newthread.daemon = True
        newthread.start()
        #WIP
    def device(self, name):
        def thread():
            if(self.display.text == 'Favorite'):
                setUserPrefs('favoriteDevice', name)
                self.display.text = ''
                alert('Added new favorite: ' + name)
            else:
                payload = {'device_ids':[devicesDict[name]]}
                print(payload)
                r = requests.put("https://api.spotify.com/v1/me/player", json=payload, headers={'Authorization': token})
                print(r.status_code, r.reason)
                #Play on fav Playlist
                if (getUserPrefs('favoritePlaylist')):
                    time.sleep( 1 )
                    payload = {'context_uri': 'spotify:user:' + userId + ':playlist:' + getUserPrefs('favoritePlaylist')}
                    print (payload)
                    r = requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
                    print(r.status_code, r.reason)
                    time.sleep( 1 )
                    r = requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})
                    print(r.status_code, r.reason)

        newthread = threading.Thread(target = thread)
        newthread.daemon = True
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
        newthread.daemon = True
        newthread.start()

    def playlist(self, name):
        def thread():
            print (self.display.text)
            if(self.display.text == 'Favorite'):
                setUserPrefs('favoritePlaylist', playlistDict[name])
                self.display.text = ''
                alert('Added new favorite: ' + name)
            else:
                if (playBackInfo['device'] == '' and getUserPrefs('favoriteDevice') in devicesDict):
                    payload = {'device_ids':[devicesDict[getUserPrefs('favoriteDevice')]]}
                    r = requests.put("https://api.spotify.com/v1/me/player", json=payload, headers={'Authorization': token})
                    print(r.status_code, r.reason)
                    time.sleep( 1 )
                payload = {'context_uri': 'spotify:user:' + userId + ':playlist:' + playlistDict[name]}
                requests.put("https://api.spotify.com/v1/me/player/play", json=payload, headers={'Authorization': token})
                time.sleep( 1 )
                requests.put("https://api.spotify.com/v1/me/player/shuffle?state=true", headers={'Authorization': token})

        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()

    pass

class SettingsPage(BoxLayout):
    def __init__(self,screen,name,**kwargs):
        super(SettingsPage,self).__init__(**kwargs)
        self.rv.viewclass.screen = screen
        self.rv.viewclass.page = self
        self.name = name
        self.entry = ''
        self.display.text = ''
        self.settingsDict = {'Choose Cast Device','Choose Backup Playlist' ,'Link Spotify'}
        self.populate(self.settingsDict)
        self.selectedSetting = ''

    def back(self):
        self.populate(self.settingsDict)
        self.selectedSetting = ''
        #set screen to home
        sm.current = 'home'
        

    def populate(self, listDict):
        self.rv.data = [{'value': x} for x in listDict]

    def setting(self, settingType):
        if (self.selectedSetting == 'Cast'):
            setUserPrefs('favoriteCastDevice', settingType)
            self.display.text = ''
            self.populate(self.settingsDict)
            self.selectedSetting = ''
            alert('Favorite Cast Device set: ' + settingType)
            return
        
        if (self.selectedSetting == 'Choose Backup Playlist'):
            setUserPrefs('favoriteBackupPlaylist', playlistDict[settingType])
            self.display.text = ''
            self.populate(self.settingsDict)
            self.selectedSetting = ''
            alert('Backup Playlist set: ' + settingType)
            return

        if (settingType == 'Choose Cast Device'):
            self.selectedSetting = settingType
            chromecasts = pychromecast.get_chromecasts()
            t = [cc.device.friendly_name for cc in chromecasts]
            self.populate(t)
            return

        if (settingType == 'Link Spotify'):
            newUserToken()
            return
        
        if (settingType == 'Choose Backup Playlist'):
            self.populate(playlistDict)
            self.selectedSetting = settingType
            return
        
    pass

class SettingsScreen(Screen): 
    def __init__(self,**kwargs):
        super(SettingsScreen,self).__init__(**kwargs)
        self.settingsPage = SettingsPage(self, 'Settings')
        #self.settingsDict = {'Cast'}
        #self.settingsPage.populate(self.settingsDict)
        self.add_widget(self.settingsPage)

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
    def __init__(self,**kwargs):
        super(LockScreen,self).__init__(**kwargs)
        if not getUserPrefs('loginCode'):
            #alert('Enter a new login code')
            self.newCodeLabel = Label()
            self.newCodeLabel.text = 'Enter a new login code'
            self.newCodeLabel.font_size = 36
            self.newCodeLabel.font_name = "Resources/LemonMilk.otf"
            self.newCodeLabel.color = utils.get_color_from_hex('#F05F40')
            self.newCodeLabel.center_y = 200
            self.add_widget(self.newCodeLabel)

    def btn_checkInput(self, input):
        loginCode = getUserPrefs('loginCode')
        if loginCode:
            if input == loginCode:
                #Correct code swap to home screen
                sm.current = 'home'
        else:
            #If no existing code ch
            if len(input) >= 4 and len(input) <= 8:
                setUserPrefs('loginCode', input)
                alert('Login code set')
                self.remove_widget(self.newCodeLabel)
            else:
                alert('Login code should be 4 - 8 characters')

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
sm.add_widget(SettingsScreen(name='settings'))

#Start thread after start
newthread = threading.Thread(target = mainThread)
newthread.daemon = True
newthread.start() 

class PiDemoApp(App):

    def build(self):
        return sm

if __name__ == '__main__':
    PiDemoApp().run()