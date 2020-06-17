# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import time
import json
import board
import busio
import audioio
import storage
import audiomp3
import neopixel
import digitalio
import adafruit_sdcard
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import displayio
from adafruit_display_text.label import Label

from adafruit_bitmap_font import bitmap_font
font = bitmap_font.load_font("/fonts/OstrichSans-Heavy-18.bdf")

display = board.DISPLAY
splash = displayio.Group(max_size=2)
bg_group = displayio.Group(max_size=1)
quote = displayio.Group(max_size=1, x=48, y=100)
splash.append(bg_group)
splash.append(quote)

### WiFi ###

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = digitalio.DigitalInOut(board.ESP_CS)
esp32_ready = digitalio.DigitalInOut(board.ESP_BUSY)
esp32_reset = digitalio.DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

# Verify nina-fw version >= 1.4.0
assert (
    int(bytes(esp.firmware_version).decode("utf-8")[2]) >= 4
), "Please update nina-fw to >=1.4.0."

status_light = neopixel.NeoPixel(
    board.NEOPIXEL, 1, brightness=0.2
)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Enable the speaker
speaker_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
speaker_enable.direction = digitalio.Direction.OUTPUT
speaker_enable.value = True

a = audioio.AudioOut(board.SPEAKER)

print("Init SD Card")
sdcard = None
sd_cs = digitalio.DigitalInOut(board.SD_CS)
sdcard = adafruit_sdcard.SDCard(spi, sd_cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

def displayQuote(text):
    with open("/images/quote_bg.bmp", "rb") as bitmap_file:
        bitmap = displayio.OnDiskBitmap(bitmap_file)
        tile_grid = displayio.TileGrid(bitmap, pixel_shader=displayio.ColorConverter())
        if bg_group:
            bg_group.pop()
        bg_group.append(tile_grid)

        status_label = Label(font, text=text, color=0xFFFFFF, max_glyphs=300)
        status_label.x = 0
        status_label.y = 0

        if quote:
            quote.pop()
        quote.append(status_label)

        display.show(splash)
        start = time.monotonic()
        while time.monotonic() - start < 1.0:
            pass

def postToAPI(endpoint, data):
    headers = {"x-api-key": secrets['x-api-key']}
    response = wifi.post(endpoint, json=data, headers=headers, timeout=30)
    data = response.json()
    print("JSON Response: ", data)
    response.close()
    return data

def downloadfile(url, filename):
    chunk_size = 4096
    r = wifi.get(url, stream=True)

    content_length = int(r.headers["content-length"])
    remaining = content_length
    print("Downloading file as ", filename)
    file = open(filename, "wb")
    for i in r.iter_content(min(remaining, chunk_size)):
        print(remaining)
        remaining -= len(i)
        file.write(i)
    file.close()
    r.close()
    print("Download done")

def playMP3(filename):
    data = open(filename, "rb")
    mp3 = audiomp3.MP3Decoder(data)
    a.play(mp3)
    while a.playing:
        pass
    mp3.deinit()

def synthesizeSpeech(data):
    response = postToAPI(secrets['endpoint'], data)
    downloadfile(response['url'], '/sd/cache.mp3')
    displayQuote(response['text'])
    playMP3("/sd/cache.mp3")

def speakText(text, voice):
    data = { "text": text, "voiceId": voice }
    synthesizeSpeech(data)

def speakQuote(tags, voice):
    data = { "tags": tags, "voiceId": voice }
    synthesizeSpeech(data)

# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")

displayQuote("Ready!")

speakText('Hello world! I am an Adafruit PyPortal running Circuit Python speaking to you using AWS Serverless', 'Joanna')

while True:
    speakQuote('equality, humanity', 'Joanna')
    time.sleep(60*secrets['interval'])
