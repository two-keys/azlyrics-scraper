from bs4 import BeautifulSoup
import requests
import json
import re
from time import sleep

agent = 'Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) \
        Gecko/20100101 Firefox/24.0'
headers = {'User-Agent': agent}
base = "azlyrics.com/"

def try_connection(tries_left, query_url, in_headers=None):
    result = None
    try:
        if headers == None:
            result = requests.get(query_url).text
        else:
            result = requests.get(query_url, headers=in_headers).text
    except:
        if tries_left > 0:
            print("Failed to send request, attempts left: ",tries_left)
            sleep(30) # wait a minute
            result = try_connection(tries_left - 1, query_url)
        else:
            print("Ran out of tries.")
    else:
        sleep(15)
    return result

def find_latest(url):
    query_url = 'http://web.archive.org/cdx/search/cdx?url=' + url + '&collapse=digest&from=20120903185847&to=20180720043037&output=json'
    print("Query_url:", query_url)
    urls = try_connection(5, query_url)
    if urls is None:
        urls = '[]'
    parse_url = json.loads(urls) # gets json
    url_list = []
    for i in range(1,len(parse_url)):
        orig_url = parse_url[i][2]
        tstamp = parse_url[i][1]
        status = int(parse_url[i][4])
        if status == 200:
            waylink = tstamp+'/'+orig_url
            url_list.append(waylink)
    ## Compiles final url pattern.
    print("Found ",len(url_list)," valid urls for ",url)
    final_url = None
    for url in url_list:
        final_url = 'https://web.archive.org/web/'+url
    return final_url

def artists(letter):
    if letter.isalpha() and len(letter) is 1:
        letter = letter.lower()
        url = base + letter + ".html"
        url = find_latest(url)
        req = requests.get(url, headers=headers)
        data = []
        if req.status_code != requests.codes.ok:
            return json.dumps(data)
        soup = BeautifulSoup(req.content, "html.parser")
        for div in soup.find_all("div", {"class": re.compile("inn|container main-page")}):
            links = div.findAll('a')
            for a in links:
                url_name = a['href']
                url_name_stripped = re.search('[^/]+(?=\.html)', url_name)
                if url_name_stripped is not None:
                    url_name = url_name_stripped.group(0)
                    data.append({"name": a.text.strip(), "url": url_name})
                else:
                    print(a.text.strip()," could not be found on azlyrics.","href:",a['href'])
        return json.dumps(data)
    else:
        raise Exception("Unexpected Input")


def songs(artist):
    artist = artist.lower().replace(" ", "")
    first_char = artist[0]
    check_url = base+first_char+"/"+artist+".html"
    url = find_latest(check_url)

    artist = {
        'artist': artist,
        'albums': {}
        }
    if url is None:
        failed_url = check_url
        print("Could not find an entry for ", failed_url)
        artist['albums'] = []
        return artist
    req = requests.get(url, headers=headers)

    soup = BeautifulSoup(req.content, 'html.parser')

    all_albums = soup.find('div', id="listAlbum")
    if all_albums is not None:
        first_album = all_albums.find('div', class_='album')
        album_name = first_album.b.text.strip('"')
        print("Found album by ",artist['artist'],":",album_name)
        songs = []

        for tag in first_album.find_next_siblings(['a', 'div']):
            if tag.has_attr('class'):
                tag_class = tag['class'][0]
                if tag_class == 'album':
                    artist['albums'][album_name] = songs
                    songs = []
                    if tag.b is None:
                        pass
                    elif tag.b:
                        album_name = tag.b.text.strip('"')

                elif tag_class == "listalbum-item":
                    song_tag = tag.contents[0]
                    if song_tag.text is "":
                        pass
                    elif song_tag.text:
                        url_name = song_tag['href']
                        url_name = re.search('[^/]+(?=\.html)', url_name).group(0)
                        songs.append({"name": tag.text, "url": url_name})
            elif tag.name == 'a':
                print("Found song?", tag)
                # this is probably an album item / song from before listalbum-item was added as a class
                if tag.has_attr('target'):
                    # all songs have target="_blank" in our timeframe
                    song_tag = tag
                    if song_tag.text is "":
                        pass
                    elif song_tag.text:
                        url_name = song_tag['href']
                        url_name = re.search('[^/]+(?=\.html)', url_name).group(0)
                        songs.append({"name": tag.text, "url": url_name})
        artist['albums'][album_name] = songs
    else:
        return None
    return artist


def lyrics(artist, song):
    artist = artist.lower().replace(" ", "")
    song = song.lower().replace(" ", "")
    url = base + "lyrics/" + artist + "/" + song + ".html"
    url = find_latest(url)
    req = try_connection(5, url, headers)
    if req is None:
        req = ''
    soup = BeautifulSoup(req.content, "html.parser")
    l = soup.find_all("div", attrs={"class": None, "id": None})
    if not l:
        return {'Error': 'Unable to find ' + song + ' by ' + artist}
    elif l:
        l = [x.getText() for x in l]
        return l
