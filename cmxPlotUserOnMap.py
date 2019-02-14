'''
Instructions:
    - Fill in the following variables
        - macAddressToLocate
            - Enter the MAC address of what you want to locate
        - cmxServerIP
            - Your CMX server IP address
        - cmxUsername
            - Your CMX API username
        - cmxUsername
            - Your CMX API password
    - Run from CLI command
        - python cmxPlotUserOnMap.py
    - Open the resulting output file "client-location.png"
Tested on:
    - CMX Version: 10.5.1-24
    - Python: 3.6.4
    - Requests: 2.18.4
    - Pillow: 5.4.1
Notes:
    - This code is written to be understandable not stylistic 
    - The code should be easily modifiable to try new things
'''

import requests # For REST API requests
import sys # For exiting the script
from PIL import Image, ImageDraw # Use Pillow module for Image
from io import BytesIO # For converting requests content to Image resource
import urllib3 # For disabling self-signed certificate complaints

macAddressToLocate = "00:01:12:23:45:56"
cmxServerIP = "10.10.10.10"
cmxUsername = "cmxUsername"
cmxPassword = "cmxPassword"

outputImageFile = "client-location.png"
circleColor = (255,0,0) # R,G,B
clientCircleSize = 100 # Number of pixels for radius of circle representing client location
resultImageMaxPixels = 800 # Use to scale the output image to a size that fits most screens
verifyCertificate = False # Set to true if not using self signed certificates

cmxServerURL = "https://{0}/api".format(cmxServerIP)
clientHistoryAPI = "{0}/location/v1/history/clients/".format(cmxServerURL)
floorInformationAPI = "{0}/config/v1/maps/info/".format(cmxServerURL)
floorImageAPI = "{0}/config/v1/maps/image/".format(cmxServerURL)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # Hide console complaints of no cert auth

def callClientHistoryAPI(macAddressToLocate):
    clientHistoryURL = clientHistoryAPI + macAddressToLocate
    r = requests.get(clientHistoryURL, verify=verifyCertificate, auth=(cmxUsername, cmxPassword))
    if r.status_code == 200:
        jsonResponse = r.json()
        # Make sure there are history entries
        if len(jsonResponse['Records']) == 0:
            print("User not found or mac address incorrect. Exiting.")
            sys.exit(1)
        lastHistoryEntry = jsonResponse['Records'][0] # Only want the most recent history entry
        mapCoordinate = lastHistoryEntry['mapCoordinate']
        userXFeet = mapCoordinate['x']
        userYFeet = mapCoordinate['y']
        mapInfo = lastHistoryEntry['mapInfo']['mapHierarchyDetails']
        userCampus = mapInfo['campus']
        userBuilding = mapInfo['building']
        userFloor = mapInfo['floor']
        return userXFeet, userYFeet, userCampus, userBuilding, userFloor
        
def callFloorInformationAPI(userCampus, userBuilding, userFloor):
    floorInformationURL = floorInformationAPI + "{0}/{1}/{2}".format(userCampus, userBuilding, userFloor)
    r = requests.get(floorInformationURL, verify=verifyCertificate, auth=(cmxUsername, cmxPassword))
    if r.status_code == 200:
        jsonResponse = r.json()
        mapDimensions = jsonResponse['dimension']
        mapXFeet = mapDimensions['width']
        mapYFeet = mapDimensions['length']
        mapImage = jsonResponse['image']
        mapXPixels = mapImage['width']
        mapYPixels = mapImage['height']
        return mapXFeet, mapYFeet, mapXPixels, mapYPixels
    
def callFloorImageAPI(userCampus, userBuilding, userFloor):  
    floorInformationURL = floorImageAPI + "{0}/{1}/{2}".format(userCampus, userBuilding, userFloor)
    r = requests.get(floorInformationURL, verify=verifyCertificate, auth=(cmxUsername, cmxPassword))  
    if r.status_code == 200:
        return Image.open(BytesIO(r.content)) # Content is the images bytes
    
def drawClientLocationOnImage(mapImageFile, userXFeet, userYFeet, mapXFeet, mapYFeet, mapXPixels, mapYPixels):
    # Determine scale factor aka how many pixels there are in a foot (depends on map scaling)
    # Doing for X and Y because maps are not always scaled correctly (ideally scaleX = scaleY)
    scaleX = mapXPixels / mapXFeet
    scaleY = mapYPixels / mapYFeet
    userXPixels = userXFeet * scaleX
    userYPixels = userYFeet * scaleY
    # Need to place a circle of size clientCircleSize centered at x:userXPixels, y:userYPixels
    x0 = userXPixels - (clientCircleSize/2)
    y0 = userYPixels - (clientCircleSize/2)
    x1 = userXPixels + (clientCircleSize/2)
    y1 = userYPixels + (clientCircleSize/2)
    imageDraw = ImageDraw.Draw(mapImageFile) 
    imageDraw.ellipse((x0, y0, x1, y1), circleColor)
    # Scale image to a fixed size
    mapImageFile.thumbnail([resultImageMaxPixels, resultImageMaxPixels], Image.ANTIALIAS) 
    return mapImageFile

if __name__ == '__main__':
    userXFeet, userYFeet, userCampus, userBuilding, userFloor = callClientHistoryAPI(macAddressToLocate)
    mapXFeet, mapYFeet, mapXPixels, mapYPixels = callFloorInformationAPI(userCampus, userBuilding, userFloor)
    mapImageFile = callFloorImageAPI(userCampus, userBuilding, userFloor)
    newImage = drawClientLocationOnImage(mapImageFile, userXFeet, userYFeet, mapXFeet, mapYFeet, mapXPixels, mapYPixels)
    newImage.save(outputImageFile) # Save image to disk
    print("User found and plotted on map. Image saved as {0}.".format(outputImageFile))
    