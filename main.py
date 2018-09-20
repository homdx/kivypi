from __future__ import print_function
from os import environ; environ['SDL_VIDEO_ALLOW_SCREENSAVER'] = '1'
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
from multiprocessing import Queue
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
from kivy.core.window import Window
from kivy.uix.vkeyboard import VKeyboard
from functools import partial
from kivy.base import runTouchApp

os.chdir(os.path.dirname(__file__))
print("Current folder: " + os.getcwd())

WINDOWS = (osplatform.system() == "Windows")
LINUX = (osplatform.system() == "Linux")
MAC = (osplatform.system() == "Darwin")

if not LINUX:
    import browser
else:
    import wifi

root_widget = Builder.load_file('main.kv') 

sBasic = None
sAccessToken = None
sRefreshToken = None
triggerToken = None
authBaseUrl = "http://13.75.194.36"

running = 1
token = ''
devicesDict = {}
playlistDict = {}
messageQueue = Queue()

#stores data for currently packback data from Spotify
playBackInfo = {"playing": False, "volume": '', "device": '', "deviceType": '', "shuffling": False, "currentSong": 'No Linked Account', "currentArtist": '', "progress_ms": 0,"duration_ms": 0, "seekPos": 0}

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
                playBackInfo = {"playing": False, "volume": '0', "device": '', "deviceType": '', "shuffling": False, "currentSong": 'Nothing Playing', "currentArtist": '', "progress_ms": 0, "duration_ms": 0, "seekPos": 0}
                return
            if (r.status_code == 401):
                token = ''
                playBackInfo = {"playing": False, "volume": '0', "device": '', "deviceType": '', "shuffling": False, "currentSong": 'Token Expired', "currentArtist": '', "progress_ms": 0, "duration_ms": 0, "seekPos": 0}
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
            playBackInfo = {"playing": False, "volume": '0', "device": '', "deviceType": '', "shuffling": False, "currentSong": 'Connection Error', "currentArtist": '', "progress_ms": 0, "duration_ms": 0, "seekPos": 0}
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
        print("Unable to update volume")

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
            return str(data[prefData])
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
            playlistDict[item['name'].encode('utf-8')] = item['id'].encode('utf-8')
        
        return playlistDict
    except Exception as e:
        print("Unable to get playlist data" + e.message)
        return
        
#Get current Spotify users devices   
def getUserDevices():
    def thread():
        try:
            global devicesDict
            r = requests.get("https://api.spotify.com/v1/me/player/devices", headers={'Authorization': token}, timeout=10)
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

def checkIP():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return 'Cant Connect'

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
            r = requests.post(authBaseUrl + ":8080/refresh_token", data={'refresh_token': sRefreshToken}, timeout=10)
        else:
            return
        if 'access_token' in r.json():
            token = r.json()['token_type'] + ' ' + r.json()['access_token']
    except Exception as e:
        print (e.message)
        return

def newUserToken():
    if not serverRunning():
        startHandler()
    
    ip = checkIP()
    split = ip.split('.')
    print (split)
    code = split[len(split)-1]
    messageQueue.put('1. Open "' + authBaseUrl + ':8080/login' + '" on phone / browser\n2. Login to Spotify account\n3. Enter code: "' + code + '" and click "Pass token to Pi"')

def openCefBrowser():
    def startCefBrowserThread():
        browser.run()
    newthread = threading.Thread(target = startCefBrowserThread)
    newthread.daemon = True
    newthread.start()

def startHandler():
    def startHandlerThread():
        ip = checkIP()
        tokenHandler.run(ip)
    newthread = threading.Thread(target = startHandlerThread)
    newthread.daemon = True
    newthread.start()

def initToken(link):
    readTokenData()
    refreshToken()
    if (token is not ''):
        getSpotifyData()
        if link:
            messageQueue.put('Linked Spotify Account: ' + userDisplayName)

def serverRunning():
    try:
        ip = checkIP()
        baseURL = "http://"+ ip +"/serverRunning"
        r = requests.get(baseURL)
        if r.status_code == 200:
            #alert exit app and link from browser
            return True
        else:
            return False
    except:
        return False

#Initialize token data 0 being that we are not linking a new account
initToken(0)
if (sRefreshToken is None):
    startHandler()

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

def updateScreen():
    while running:
        if (running == 0):
            break
        if (sRefreshToken is None):
                time.sleep( 1 )
                continue
        for x in range(0, 600): 
            if (running):
                time.sleep( 1 )
                try:
                    sm.get_screen('home').updateProgess()
                except:
                    print ("No such screen / error updating progress")
            else:
                break

def messageWorker():
    while True:
        item = messageQueue.get()
        alert(item)
        #messageQueue.task_done()

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
                        messageQueue.put('Already in Favorite Playlist')
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
                        messageQueue.put('Nothing playing')
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
                        messageQueue.put('Track not in Favorite Playlist')
                        return

                    r = requests.get("https://api.spotify.com/v1/users/" + userId + "/playlists/" + backPlaylist, headers={'Authorization': token})
                    if trackId not in r.text:
                        p = requests.post("https://api.spotify.com/v1/users/" + userId + "/playlists/" + backPlaylist + "/tracks?uris=spotify%3Atrack%3A" + trackId, headers={'Authorization': token})
                        if (p.status_code < 400):
                            print("Added to Backup Playlist")
                    
                except:
                    messageQueue.put('Error adding to playlist')
                    return
            else:
                messageQueue.put('You need a Favorite and Backup playlist to do this')

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
                favoriteDevice = str(getUserPrefs('favoriteDevice'))
                if (r.status_code == 204):#Nothing playing
                    if (favoriteDevice and favoriteDevice in devicesDict):
                        payload = {'device_ids':[devicesDict[favoriteDevice]]}
                        r = requests.put("https://api.spotify.com/v1/me/player", json=payload, headers={'Authorization': token})
                        print(r.status_code, r.reason)
                        time.sleep( 1 )
                        r = requests.get("https://api.spotify.com/v1/me/player", headers={'Authorization': token})
                        playing = r.json()['is_playing']
                        return
                    else:
                        messageQueue.put('No Favorite Device or Favorite Device not available')
                else:
                    if (r.status_code == 400):
                        messageQueue.put('Bad request: ' + r.json()['error']['message'])
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
                messageQueue.put('Unable to play on favorite device: ' + e.message)
            except Exception as e:
                messageQueue.put('Error playing or no favorite device: ' + e.message)


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

            #number of videos to play
            vidCount = '100'
            vidCountMax = 50
            watchedVideoPath = 'WatchedVideoLog.txt'

            def f(x):
                return {
                'month': "https://www.reddit.com/r/YoutubeHaiku/top.json?sort=top&t=month&limit=" + vidCount,
                'week': "https://www.reddit.com/r/YoutubeHaiku/top.json?sort=top&t=week&limit=" + vidCount,
                'day': "https://www.reddit.com/r/YoutubeHaiku/top.json?sort=top&t=day&limit=" + vidCount
                }.get(x, "https://www.reddit.com/r/YoutubeHaiku/top.json?sort=top&t=day&limit=" + vidCount)

            def checkWatched(url):
                if not os.path.isfile(watchedVideoPath):
                    return False
                with open(watchedVideoPath) as f:
                    lines = f.readlines()
                    for x in lines:
                        if str(url)+'\n' == x:
                            return True
                return False

            def setWatched(url):
                f=open(watchedVideoPath, "a+")
                f.write(url+'\n')
                f.close

            if(not getUserPrefs('favoriteCastDevice')):
                messageQueue.put('Select a default Cast device in settings')
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
                if len(thislist) >= vidCountMax:
                    break
                innerData = c['data']
                x = innerData['url']
                x = x.replace('%26', '&')
                x = x.replace('%3D', '=')
                if ('?start' in x):
                    print ('Skipping vid: ' + x)
                    continue
                elif ('attribution_link' in x):
                    vidId = find_between(x, 'v=', '&')
                    if not checkWatched(vidId):
                        thislist.append(vidId)
                        checkLast(thislist[-1], x, 5)
                    continue
                elif('?t=' in x):
                    vidId = find_between(x, 'be/', '?')
                    if not checkWatched(vidId):
                        thislist.append(vidId)
                        checkLast(thislist[-1], x, 5)
                    continue
                elif ('&' in x):
                    vidId = find_between(x, 'v=', '&')
                    if not checkWatched(vidId):
                        thislist.append(vidId)
                        checkLast(thislist[-1], x, 5)
                    continue
                elif('be/' in x):
                    vidId = find_from(x, 'be/')
                    if not checkWatched(vidId):
                        thislist.append(vidId)
                        checkLast(thislist[-1], x, 5)
                    continue
                elif('v=' in x):
                    vidId = find_from(x, 'v=')
                    if not checkWatched(vidId):
                        thislist.append(vidId)
                        checkLast(thislist[-1], x, 5)
                    continue
                else:
                    print("Invalid url: " + x)

            if len(thislist) is 0:
                messageQueue.put('All videos marked as watched')
                return

            # Triggers program exit
            shutdown = Event()

            def signal_handler(x,y):
                shutdown.set()

            chromecasts = pychromecast.get_chromecasts()
            print([cc.device.friendly_name for cc in chromecasts])

            if(len(chromecasts) == 0):
                messageQueue.put('No cast devices found')
                return

            if(getUserPrefs('favoriteCastDevice') not in [cc.device.friendly_name for cc in chromecasts]):
                messageQueue.put('Favorite device ' + getUserPrefs('favoriteCastDevice') + '  not Available')
                return

            cast = next(cc for cc in chromecasts if cc.device.friendly_name == getUserPrefs('favoriteCastDevice'))
            # Wait for cast device to be ready
            cast.wait()
            mc = cast.media_controller

            # Create and register a YouTube controller
            yt = YouTubeController()
            cast.register_handler(yt)

            # Play the video ID we've been given
            if len(thislist) is not 0:
                setWatched(thislist[0])
                yt.play_video(thislist[0])
                thislist.remove(thislist[0])

            for x in thislist:
                setWatched(x)
                yt.add_to_queue(x)

        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()

    def btn_startCastAll(self):

        def thread():
            filename = "YTTopWeek_All.txt"

            if(not getUserPrefs('favoriteCastDevice')):
                messageQueue.put('Select a default Cast device in settings')
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
                messageQueue.put('No cast devices found')
                return

            if(getUserPrefs('favoriteCastDevice') not in [cc.device.friendly_name for cc in chromecasts]):
                messageQueue.put('Favorite device ' + getUserPrefs('favoriteCastDevice') + '  not Available')
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

    def runServer(self):
        newUserToken()

    def checkRunning(self):
        if(serverRunning()):
            messageQueue.put('Running')

    def btn_exit(self):
        global running
        running = 0
        App.get_running_app().stop()

    def btn_checkIP(self):
        def thread():
            oldtime = time.time()
            while self.ids.IP.state == "down":
                #if user holds down for 2 seconds open debug Popup
                if time.time() - oldtime > 3:
                    #messageQueue.put('Opening Debug')
                    DebugPopup(self).open()
                    break
        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()

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
        if triggerToken is not None:
            r = requests.post("https://www.triggercmd.com/api/ifttt?trigger=Lock&computer=NickDesktop", data={'token': triggerToken})
            print(r.status_code, r.reason)
            print(r.text[:300] + '...')

    def btn_trainTimetable(self):
        webbrowser.open('https://anytrip.com.au/stop/au2:206020')

    def btn_refresh(self):
        refreshToken()

    pass

class DebugPopup(Popup):
    def __init__(self,screen,**kwargs):
        super(DebugPopup,self).__init__(**kwargs)
        self.screen = screen
        self.size_hint = (.5, .5)
        self.title = 'Choose Branch'
        layout = BoxLayout(spacing=10, orientation="vertical")
        layout.add_widget(Button(text="develop", on_press=self.changeBranch))
        layout.add_widget(Button(text="test", on_press=self.changeBranch))
        layout.add_widget(Button(text="beta", on_press=self.changeBranch))
        layout.add_widget(Button(text="master", on_press=self.changeBranch))
        self.add_widget(layout)

    def changeBranch(self, button):
        try:
            print(button.text)
            if LINUX:
                import git
                git_dir = os.getcwd()
                g = git.cmd.Git(git_dir)
                g.checkout(button.text)
        except Exception as e:
            print("unable to checkout branch: " + e.message)
            messageQueue.put('Unable to checkout branch')

class WifiScreen(Screen):

    def __init__(self, wifiName, **kwargs):
        super(WifiScreen, self).__init__(**kwargs)
        self.title = 'Enter Wifi Password'
        self.wifiName = wifiName
        layout = BoxLayout(orientation="vertical")
        layout.add_widget(Button(text='Enter Wifi Password: ' + self.wifiName, on_press=self.closeScreen))
        self.pw = Label(text='',)
        self.userInput = ''
        layout.add_widget(self.pw)
        layout.add_widget(Button(text="Back", on_press=self.closeScreen))
        self.add_widget(layout)

        self._keyboard = None
        kb = Window.request_keyboard(
            self._keyboard_close, self)
        if kb.widget:
            # If the current configuration supports Virtual Keyboards, this
            # widget will be a kivy.uix.vkeyboard.VKeyboard instance.
            self._keyboard = kb.widget
            self._keyboard.layout = 'qwerty'
        else:
            self._keyboard = kb

        self._keyboard.bind(on_key_down=self.key_down,
                            on_key_up=self.key_up)

    def updateInput(self, input):
        self.userInput = self.userInput + input
        self.pw.text =  self.pw.text + '*'
        return

    def deleteInput(self):
        self.userInput = self.userInput[:-1]
        self.pw.text =  self.pw.text[:-1]
        return

    def closeScreen(self):
        Window.release_all_keyboards()
        sm.current = 'home'
        sm.remove_screen(sm.get_screen('wifi'))

    def _keyboard_close(self, *args):
        """ The active keyboard is being closed. """
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self.key_down)
            self._keyboard.unbind(on_key_up=self.key_up)
            self._keyboard = None

    def key_down(self, keyboard, keycode, text, modifiers):
        """ The callback function that catches keyboard events. """
        return

    # def key_up(self, keyboard, keycode):
    def key_up(self, keyboard, keycode, *args):
        """ The callback function that catches keyboard events. """
        if keycode == None:
            print('none')
            return
        
        if isinstance(keycode, tuple):
            keycode = keycode[1]

        if keycode == 'backspace':
            self.deleteInput()
            return

        if keycode == 'capslock' or keycode == 'shift' or keycode == 'layout' or keycode == 'tab':
            print('retuning')
            return

        if keycode == 'enter':
            if (not self.Connect(self.wifiName, self.userInput)):
                messageQueue.put('Unable to connect to network: ' self.wifiName)
            self.closeScreen()
            return

        if keycode == 'escape':
            Window.release_all_keyboards()
            self.closeScreen()
            return
        # system keyboard keycode: (122, 'z')
        # dock keyboard keycode: 'z'

        self.updateInput(keycode)

    def Search(self):
        wifilist = []

        cells = wifi.Cell.all('wlan0')

        for cell in cells:
            wifilist.append(cell)

        return wifilist

    def FindFromSearchList(self, ssid):
        wifilist = self.Search()

        for cell in wifilist:
            if cell.ssid == ssid:
                return cell

        return False


    def FindFromSavedList(self, ssid):
        cell = wifi.Scheme.find('wlan0', ssid)

        if cell:
            return cell

        return False

    def Connect(self, ssid, password=None):
        cell = self.FindFromSearchList(ssid)

        if cell:
            savedcell = self.FindFromSavedList(cell.ssid)

            # Already Saved from Setting
            if savedcell:
                savedcell.activate()
                return cell

            # First time to conenct
            else:
                if cell.encrypted:
                    if password:
                        scheme = self.Add(cell, password)

                        try:
                            scheme.activate()

                        # Wrong Password
                        except wifi.exceptions.ConnectionError:
                            self.Delete(ssid)
                            return False

                        return cell
                    else:
                        return False
                else:
                    scheme = self.Add(cell)

                    try:
                        scheme.activate()
                    except wifi.exceptions.ConnectionError:
                        self.Delete(ssid)
                        return False

                    return cell
        
        return False

    def Add(self, cell, password=None):
        if not cell:
            return False

        scheme = wifi.Scheme.for_cell('wlan0', cell.ssid, cell, password)
        scheme.save()
        return scheme


    def Delete(self, ssid):
        if not ssid:
            return False

        cell = self.FindFromSavedList(ssid)

        if cell:
            cell.delete()
            return True

        return False

class VolumePopup(Popup):

    def __init__(self,screen,**kwargs):
        super(VolumePopup,self).__init__(**kwargs)
        self.screen = screen
        global playBackInfo
        self.volume = playBackInfo['volume']
    
    def closeandUpdate(self):
        def thread():
            setVolume(self.screen.volume_buttonText)
        #the number from the slider is a decimal/float, convert it to a whole number before using it
        self.screen.volume_buttonText = self.screen.volume_buttonText.split(".")[0]
        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()
        self.dismiss()

    def exitandUpdate(self):
        def thread():
            global playBackInfo
            self.screen.volume_buttonText = playBackInfo['volume']
        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()
        self.dismiss()

    def btn_volDown(self):
        def thread():
            global playBackInfo
            volumeUpdate = int(playBackInfo['volume'])-1
            setVolume(volumeUpdate)
            self.screen.volume_buttonText = str(volumeUpdate)    
        newthread = threading.Thread(target = thread)
        newthread.daemon = True
        newthread.start()

    def btn_volUp(self):
        def thread():
            global playBackInfo
            volumeUpdate = int(playBackInfo['volume'])+1
            setVolume(volumeUpdate)
            self.screen.volume_buttonText = str(volumeUpdate)    
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

class KeyboardScreen(Screen):
    """
    Screen containing all the available keyboard layouts. Clicking the buttons
    switches to these layouts.
    """
    displayLabel = ObjectProperty()
    kbContainer = ObjectProperty()

    def __init__(self, **kwargs):
        super(KeyboardScreen, self).__init__(**kwargs)
        self._add_keyboards()
        self._keyboard = None

    def _add_keyboards(self):
        """ Add a buttons for each available keyboard layout. When clicked,
        the buttons will change the keyboard layout to the one selected. """
        layouts = list(VKeyboard().available_layouts.keys())
        # Add the file in our app directory, the .json extension is required.
        #layouts.append("numeric2.json")
        for key in layouts:
            self.kbContainer.add_widget(
                Button(
                    text=key,
                    on_release=partial(self.set_layout, key)))

    def set_layout(self, layout, button):
        """ Change the keyboard layout to the one specified by *layout*. """
        kb = Window.request_keyboard(
            self._keyboard_close, self)
        if kb.widget:
            # If the current configuration supports Virtual Keyboards, this
            # widget will be a kivy.uix.vkeyboard.VKeyboard instance.
            self._keyboard = kb.widget
            self._keyboard.layout = layout
        else:
            self._keyboard = kb

        self._keyboard.bind(on_key_down=self.key_down,
                            on_key_up=self.key_up)

    def _keyboard_close(self, *args):
        """ The active keyboard is being closed. """
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self.key_down)
            self._keyboard.unbind(on_key_up=self.key_up)
            self._keyboard = None

    def key_down(self, keyboard, keycode, text, modifiers):
        """ The callback function that catches keyboard events. """
        self.displayLabel.text = u"Key pressed - {0}".format(text)

    # def key_up(self, keyboard, keycode):
    def key_up(self, keyboard, keycode, *args):
        """ The callback function that catches keyboard events. """
        # system keyboard keycode: (122, 'z')
        # dock keyboard keycode: 'z'
        if isinstance(keycode, tuple):
            keycode = keycode[1]
        self.displayLabel.text += u" (up {0})".format(keycode)

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
                messageQueue.put('Added new favorite: ' + name)
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
                messageQueue.put('Added new favorite: ' + name)
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
        self.settingsDict = {'Choose Cast Device','Choose Backup Playlist', 'Disable Lock Screen'}
        if LINUX:
            self.settingsDict = {'Choose Cast Device','Choose Backup Playlist', 'Disable Lock Screen', 'Wifi'}
        self.populate(self.settingsDict)
        self.selectedSetting = ''

    def back(self):
        self.populate(self.settingsDict)
        self.selectedSetting = ''
        #set screen to home2 (settings page)
        sm.current = 'home2'

    def Search(self):
        wifilist = []

        cells = wifi.Cell.all('wlan0')

        for cell in cells:
            wifilist.append(cell)

        return wifilist

    def populate(self, listDict):
        self.rv.data = [{'value': x} for x in listDict]

    def setting(self, settingType):
        if (self.selectedSetting == 'Wifi'):
            sm.add_widget(WifiScreen(name="wifi", wifiName=settingType))
            sm.current = 'wifi'
            self.display.text = ''
            self.populate(self.settingsDict)
            self.selectedSetting = ''
            return

        if (self.selectedSetting == 'Cast'):
            setUserPrefs('favoriteCastDevice', settingType)
            self.display.text = ''
            self.populate(self.settingsDict)
            self.selectedSetting = ''
            messageQueue.put('Favorite Cast Device set: ' + settingType)
            return
        
        if (self.selectedSetting == 'Choose Backup Playlist'):
            setUserPrefs('favoriteBackupPlaylist', playlistDict[settingType])
            self.display.text = ''
            self.populate(self.settingsDict)
            self.selectedSetting = ''
            messageQueue.put('Backup Playlist set: ' + settingType)
            return

        if (settingType == 'Choose Cast Device'):
            self.selectedSetting = 'Cast'
            chromecasts = pychromecast.get_chromecasts()
            t = [cc.device.friendly_name for cc in chromecasts]
            self.populate(t)
            return

        if (settingType == 'Link Spotify'):
            newUserToken()
            return
        
        if (settingType == 'Choose Backup Playlist'):
            print(playlistDict)
            self.populate(playlistDict)
            self.selectedSetting = settingType
            return
        if (settingType == 'Disable Lock Screen'):
            if (getUserPrefs('lockScreenDisabled') == '1'):
                setUserPrefs('lockScreenDisabled', '0')
                messageQueue.put('Lock screen reenabled')
            else:
                setUserPrefs('lockScreenDisabled', '1')
                messageQueue.put('Lock screen disabled')
            self.selectedSetting = settingType
            return
        if (settingType == 'Wifi'):
            print(self.Search())
            wifiDict = {}
            id = 0
            for item in self.Search():
                wifiDict[item.ssid] = id
                id = id+1
            print (wifiDict)
            self.populate(wifiDict)
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
    displayText = StringProperty('')
    def __init__(self,**kwargs):
        super(LockScreen,self).__init__(**kwargs)
        self.userInput = ''
        if not getUserPrefs('loginCode'):
            self.newCodeLabel = Label()
            self.newCodeLabel.text = 'Enter new login code'
            self.newCodeLabel.font_size = 36
            self.newCodeLabel.font_name = "Resources/LemonMilk.otf"
            self.newCodeLabel.color = utils.get_color_from_hex('#F05F40')
            self.newCodeLabel.center_y = 225
            self.add_widget(self.newCodeLabel)

    def updateInput(self, input):
        self.userInput = self.userInput + input
        self.displayText = self.displayText + '*'
        return

    def deleteInput(self):
        self.userInput = self.userInput[:-1]
        self.displayText = self.displayText[:-1]
        return

    def btn_checkInput(self):
        loginCode = getUserPrefs('loginCode')
        if loginCode:
            if self.userInput == loginCode:
                #Correct code swap to home screen
                sm.current = 'home'
        else:
            #If no existing code ch
            if len(self.userInput) >= 4 and len(self.userInput) <= 8:
                setUserPrefs('loginCode', self.userInput)
                messageQueue.put('Login code set')
                self.remove_widget(self.newCodeLabel)
            else:
                messageQueue.put('Login code should be 4 - 8 characters')

        self.userInput = ''
        self.displayText = ''

# Create the screen manager
sm = ScreenManager()
sm.add_widget(LockScreen(name='lock'))
sm.add_widget(HomeScreen(name='home'))
sm.add_widget(HomeScreen2(name='home2'))
sm.add_widget(CalandarScreen(name='calandar'))
sm.add_widget(PlaylistScreen(name='playlists'))
sm.add_widget(DevicesScreen(name='devices'))
sm.add_widget(SettingsScreen(name='settings'))
sm.add_widget(KeyboardScreen(name="keyboard"))

if(getUserPrefs('lockScreenDisabled') == '1'):
    sm.current = 'home'

#Start thread after start
main = threading.Thread(target = mainThread)
main.daemon = True
main.start() 

#update localdata for screen
update = threading.Thread(target = updateScreen)
update.daemon = True
update.start() 

#worker thread for alert messages
worker = threading.Thread(target=messageWorker)
worker.daemon = True
worker.start()

class PiDemoApp(App):

    def build(self):
        return sm

if __name__ == '__main__':
    PiDemoApp().run()