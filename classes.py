import requests
import json
from datetime import date
from lxml import html
import mylogging as log
import functs

encoding_string = functs.encoding_string
lang_handling = functs.lang_handling
replace_accent = functs.replace_accent
download = functs.download


class TV2:
    def __init__( self, host, lang, settings={ 'bitrate': 720, 'path': 'tmp' } ):
        self.host_settings = host
        self.host_settings['date_end'] = date.today().strftime("%Y-%m-%d")

        self.settings = settings

        self.lang = lang


    def data_mining( self, link, xpath_desc ):
        '''Adatok halászása az adott hivatkozásról'''
        try:
            page = requests.get( link )
        except requests.exceptions.InvalidURL:
            log.error( encoding_string( self.lang["errors"]["url"].format( link=link ) ) )
            return False
        except requests.exceptions.ConnectionError:
            log.error( encoding_string( self.lang["errors"]["con"].format( link=link ) ) )
            return False

        tree = html.fromstring( page.content )
        return tree.xpath( xpath_desc )


    def get_series(self):
        '''Visszaadja a host összes sorozatát egy rendezett listában'''
        series_l = []
        host = self.host_settings['host']
        xpath_desc = self.host_settings['series_xpath']

        print( '\n{load}...'.format( load=lang_handling( "load", self.lang ) ), end='' )

        series = self.data_mining( '{host}/search.php'.format( host=host ), xpath_desc )
        if not series:
            return False

        for value in series:
            key = value.xpath('text()')[0].lower().strip()
            val = value.xpath('@value')[0]

            if val != '0': #0 - Műsor (alapértelmezett menüpont)
                series_l.append( ( key, val ) )

        print( '{ready}'.format( ready=lang_handling( "ready", self.lang ) ) )

        return sorted( series_l, key=lambda series_l: replace_accent( series_l[0] ) )


    def search_series( self, series ):
        '''Megkeresi a listában a megadott kulcsszót'''
        hit_series = []

        while True:
            keyword = input( '\n{search}: '.format( search=lang_handling( "series_search", self.lang ) ) )

            if len( keyword ) < 3:
                log.warning( encoding_string( self.lang["errors"]["min"] ) )
                continue
            else:
                break

        for ser in series:
            if keyword.lower() in ser[0]:
                hit_series.append( ser )

        if len( hit_series ) == 0:
            log.warning( encoding_string( self.lang["errors"]["non"].format( key=keyword ) ) )
            return False

        return hit_series


    def print_series( self, series ):
        '''Kiírja a letölthető sorozatokat és visszatér a kiválasztott azonosítójával'''
        while True:

            print( '\n{id:^15}{name}'.format( id=lang_handling( "identification", self.lang ), name=lang_handling( "series", self.lang ) ) )
            print( '-' * 40 )
            for i in range( len( series ) ):
                print( '{id:^15}{name}'.format( id=i, name=series[i][0].capitalize() ) )
            
            series_id = input('\n{ident}: '.format( ident=lang_handling( "identification", self.lang ) ) )

            if not series_id.isdigit() or int( series_id ) >= len( series ) or int( series_id ) < 0:
                log.warning( encoding_string( self.lang["errors"]["ide"].format( id=series_id ) ) )
            else:
                break

        self.settings['show_id'] = series[ int(series_id) ][1]
        self.settings['show_name'] = series[int(series_id)][0].capitalize()

        log.debug( encoding_string( self.lang["selected_series"].format( series=series[int(series_id)][0] ) ) )
        log.debug( encoding_string( self.lang["selected_series_id"].format( id=series[int(series_id)][1] ) ) )



    def valid_episodes( self, episodes ):
        '''Megvizsgálja az átadott listát'''
        for value in episodes:
            if not value.isdigit():
                log.warning( encoding_string( self.lang["errors"]["num"].format( value=value ) ) )
                return False
        return True


    def get_episodes(self):
        '''A bemenetnek megfelelően előállítja a letöltendő elemek listáját (vagy range)'''
        while True:
            episodes = input( '\n{down}: '.format( down=lang_handling( "download_episodes", self.lang ) ) )
            episodes = episodes.replace(' ','')

            if ',' in episodes:
                episodes = episodes.strip(',')
                episodes = episodes.split(',')

                if self.valid_episodes(episodes):
                    episodes = set(episodes)
                    self.settings['episodes'] = sorted( [ int(ep) for ep in episodes ] )
                    log.debug( encoding_string( self.lang['selected_episodes'].format( episodes=str( self.settings['episodes'] ) ) ) )
                    return True
                else:
                    continue

            if '-' in episodes:
                episodes = episodes.strip('-')
                episodes = episodes.split('-')

                if len( episodes ) != 2:
                    log.warning( encoding_string( self.lang["errors"]["int"] ) )
                    continue
                if self.valid_episodes(episodes):
                    episodes[0] = int( episodes[0] )
                    episodes[1] = int( episodes[1] )
                    self.settings['episodes'] = range( min(episodes), max(episodes) + 1 )
                    log.debug( encoding_string( self.lang['selected_episodes'].format( episodes=str( self.settings['episodes'] ) ) ) )
                    return True
                else:
                    continue

            if episodes.isdigit():
                self.settings['episodes'] = [ int( episodes ) ]
                log.debug( encoding_string( self.lang['selected_episodes'].format( episodes=str( self.settings['episodes'] ) ) ) )
                return True
            else:
                log.warning( encoding_string( self.lang["errors"]["num"].format( value=episodes ) ) )


    def get_episode_links( self, ep ):
        '''Visszaadja egy epizódhoz tartozó szeletek listáját'''
        xpath_desc = self.host_settings['episodes_xpath']
        host = self.host_settings['host']
        link = '{host}/search/{episode}/oldal1?&datumtol={date_start}&datumig={date_end}&musorid={show_id}'.format( host=host, episode=ep, date_start=self.host_settings['date_start'], date_end=self.host_settings['date_end'], show_id=self.settings['show_id'] )

        pager = self.data_mining( link, self.host_settings['pager_xpath'] )
        if pager == False:
            return False

        if pager:
            if 'utolsó' in pager[-1].xpath( 'text()' )[0]:
                link = host + pager[-1].xpath( '@href' )[0]
            else:
                link = host + pager[-2].xpath( '@href' )[0]

            videos = self.data_mining( link, xpath_desc )
            if not videos:
                return False
        else:
            videos = self.data_mining( link, xpath_desc )

        valid_episodes = [
            ' {episode}. '.format( episode=ep ),
            ' {episode}/1. '.format( episode=ep ),
            ' {episode}/2. '.format( episode=ep ),
            ' {episode}/3. '.format( episode=ep )
        ]

        ep_links = []

        for ep_link in videos:
            for string in valid_episodes:
                if string in ep_link.xpath( 'text()' )[0]:
                    ep_links.append( ( host + ep_link.xpath( '@href' )[0], ep_link.xpath( 'text()' )[0] ) )
                    break

        return ep_links


    def get_json_url( self, link ):
        '''Visszaadja a json fájl elérési útját'''
        xpath_desc = self.host_settings['script_xpath']

        scripts = self.data_mining( link, xpath_desc )
        if not scripts:
            return False

        start = 'jsonUrl'
        end = '&type=json'
        jsonUrl = ''

        for script in scripts:
            result = script.find( start )
            if result != -1:
                jsonUrl = ''.join( script[ result : ].split(" ") )
                jsonUrl_result = jsonUrl.find( end )
                jsonUrl = jsonUrl[ len( start ) + 2 : jsonUrl_result + len( end ) ]
                break
                
        return jsonUrl


    def get_json_dict( self, link ):
        '''Visszaad a json fájlból egy adatszótárat'''
        link = "http://{link}".format( link=link.lstrip("//") )

        jsonText = self.data_mining( link, '//text()' )
        if not jsonText:
            return False
        else:
            jsonText = jsonText[0]
        
        return json.loads( jsonText )


    def select_bitrate( self, dictionary ):
        '''A megadott felbontás vagy a megadotthoz legközelebbi kiválasztása'''
        bitrates = dictionary['mp4Labels']
        del bitrates[0]

        for i in range( len( bitrates ) ):
            if self.settings['bitrate'] >= int( bitrates[i].rstrip('p') ):
                break

        videoLinks = dictionary['bitrates']['mp4']
        del videoLinks[0]

        return videoLinks[i]

    def download_videos( self ):
        '''Letöltés vezérlő'''
        series = self.get_series()
        if not series:
            return False

        while True:
            series_hit = self.search_series( series )
            if series_hit:
                break

        self.print_series( series_hit )
        self.get_episodes()

        for ep in self.settings['episodes']:
            log.info( '-'*10 + '{ep}. {episode} '.format( ep=ep, episode=lang_handling( 'episode', self.lang ) ) + '-'*10 )
            ep_links = self.get_episode_links( ep )
            if not ep_links:
                log.warning( encoding_string( self.lang["errors"]["not"] ) )
                continue

            for ep_link, ep_name in ep_links:
                log.info( '[{ep}]'.format( ep=ep_name ) )
                jsonUrl = self.get_json_url( ep_link )
                if not jsonUrl:
                    continue

                if jsonUrl != '':
                    jsonDict = self.get_json_dict( jsonUrl )
                    if not jsonDict:
                        continue

                    link = 'http:{url}'.format( url=self.select_bitrate( jsonDict ) )
                    log.debug( link )
                    try:
                        download( link, ep_name, self.settings['path'] )
                        log.debug( lang_handling( 'done', self.lang ) )
                    except:
                        log.error( encoding_string( lang['errors']['dow'] ) )


    def __str__( self ):
        return str( self.settings )