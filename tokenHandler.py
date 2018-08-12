from flask import Flask
from flask import request
import os, json

os.chdir(os.path.dirname(__file__))
app = Flask(__name__)

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

def updateJsonFile(token, rtoken):
    if (os.path.isfile("tokenData.json") and os.stat("tokenData.json").st_size != 0):
        jsonFile = open("tokenData.json", "r") # Open the JSON file for reading
        data = json.load(jsonFile) # Read the JSON into the buffer
        jsonFile.close() # Close the JSON file
        data["sAccessToken"] = token
        data["sRefreshToken"] = rtoken
    else:
        jsonFile = open("tokenData.json", "a+") # Create the JSON file
        data = {'sAccessToken': token, 'sRefreshToken': rtoken}
        jsonFile.write(json.dumps(data))
        jsonFile.close() # Close the JSON file
        return

    ## Save our changes to JSON file
    jsonFile = open("tokenData.json", "w+")
    jsonFile.write(json.dumps(data))
    jsonFile.close()

def createMarker():
    f=open("newtoken.txt", "a+")
    f.close

@app.route('/receiveToken', methods=['POST'])
def result():
    #print(request.form['access_token'])

    updateJsonFile(request.form['access_token'], request.form['refresh_token'])
    createMarker()
    shutdown_server()
    return 'Received !' # response to your request.

@app.route('/serverRunning', methods=['GET'])
def runResult():
    #let client know server is up or not
    return 'Running'

def run():
    app.run()