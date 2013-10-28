#!/usr/bin/python
# -*- coding: utf-8  -*-
#$ -l h_rt=48:00:00
#$ -l virtual_free=100M
#$ -l arch=sol
#$ -o $HOME/coords_ghel.out

'''

import article primary coordinates from GHEL database to Wikidata
runs on Toolserver

@author Kentaur


'''


import sys, os
sys.path.append("/home/kentaur/py/pywikibot/compat")
#sys.path.append("/home/kentaur/py/pywikibot/core")
import wikipedia as pywikibot
import re, MySQLdb, time, math
import logging


# FIXME
# before posting coords recheck via API if datapage still has langlinks
# log if wiki coords and wikidata coords are too different


# output debug messages
DEBUG = False

# Wikidata pages for Wikipedias
wikiDataPage = {
    'de' : 'q48183',
    'et' : 'q200060',
    'fr' : 'q8447',
}


# functions

def connectCoordDb(lang):
    '''
    Connect to the Ghel coord database
    '''
    
    if (lang):
        hostName = lang + 'wiki-p.db.toolserver.org'
        dbName = lang + 'wiki_p'
        #coordDbName = 'u_dispenser_p'
        conn = MySQLdb.connect(host=hostName, db=dbName,
            read_default_file=os.path.expanduser("~/.my.cnf"), 
            use_unicode=True, charset='utf8')
        cursor = conn.cursor()
        return (conn, cursor)

def getPrecision(coordValue):
    precision = 0
    
    if (round(coordValue*60 - int(round(coordValue*60,2)), 2)==0):
        precision = "0.01666666666666667"  #   1' minute
    elif (round(coordValue*3600 - int(round(coordValue*3600,2)), 2)==0):
        precision = "0.00027777777777778"  #   1'' second
    elif (round(coordValue*36000 - int(round(coordValue*36000,2)), 2)==0):
        precision = "0.00002777777777778"  #   0.1'' seconds
    else:
        precision = "0.00000277777777778"  #   0.01'' seconds
    
    return precision

def hasCoordinates(dataPageId, cursor):
    hasCoordinates = True
    
    if dataPageId:
        dataPageTitle = "Q%s" % dataPageId
        query = """SELECT
        1
        FROM wikidatawiki_p.page
        JOIN wikidatawiki_p.pagelinks
        ON pl_from = page_id
        WHERE page_namespace = 0 
        AND pl_namespace = 120
        AND pl_title = 'P625'
        AND page_title = '%s'""" 
        cursor.execute(query % (dataPageTitle, )) 
        hasCoordinates = (cursor.rowcount > 0)
        if DEBUG:
            print query % (dataPageTitle, )
                       
        return hasCoordinates

def hasCoordinatesAPI(data):
    hasCoordinatesAPI = True
    
    if data.exists():
        item = data.get()
        
        claims = {}
        if 'claims' in item:
            for claim in item['claims']:
                if claim['m'][1] not in claims:
                    claims[claim['m'][1]] = []
                claims[claim['m'][1]].append(claim)
        
        try:
            coordClaim = claims[625][0]
            hasCoordinatesAPI = True
        except KeyError:
            # Key is not present
            hasCoordinatesAPI = False
    
    return hasCoordinatesAPI

def checkCoordinates(pageTitle, dataPageId, lat, lon, cursor):
    addStatus = False
    
    if DEBUG:
        print "title: %s, dataPage: %s, lat: %s, lon: %s" % (pageTitle, dataPageId, lat, lon)

    repo = site.data_repository()
          
    if dataPageId:
        if not hasCoordinates(dataPageId, cursor):
            dataPageTitle = "Q%s" % dataPageId
            data = pywikibot.DataPage(repo, dataPageTitle)
            if hasCoordinatesAPI(data):
                logging.warning('[[%s]]: coords exist, hasCoordinates() didnt catch it!' % (pageTitle )) 
                return False
            else:
                addStatus = addCoordinates(data, pageTitle, lat, lon, lang)
    elif pageTitle:
        page = pywikibot.Page(site, pageTitle)
        data = pywikibot.DataPage(page)
        if data.exists():
            print '[[%s]]: data page already exists!' % (pageTitle )
            logging.info('[[%s]]: data page already exists!' % (pageTitle )) 
        else:
            data.createitem(u"Bot: Importing article from %s.wikipedia" % lang )
            logging.info(u'[[%s]]: creating data page' % (pageTitle) )
    
        if data.exists():
            if not hasCoordinatesAPI(data):
                addStatus = addCoordinates(data, pageTitle, lat, lon, lang)  
        else:
            print 'ERROR: NO DATA PAGE'
            logging.warning('[[%s]]: no data page in Wikidata' % (pageTitle ))
        
    return addStatus

def addCoordinates(datapage, article, latitude, longitude, lang):
      
    botflag = True
    propertyID = 625 #geo coordinates
    latitudeStr = "%.12f" % (latitude)
    longitudeStr = "%.12f" % (longitude)
    
    precision = min(getPrecision(latitude), getPrecision(longitude))
        
    value = "{\"latitude\":"  + latitudeStr  + ",\"longitude\":" + longitudeStr + ",\"precision\":" + precision + ",\"globe\": \"http://www.wikidata.org/entity/Q2\"}"
    print value

    params = {
    'action': 'wbcreateclaim',
    'entity': datapage.title().replace("Q", "q"),
    'snaktype': 'value',
    'property': "p%d" % propertyID,
    'value': value,
    }
    params['token'] = datapage.site().getToken()
    if botflag:
        params['bot'] = 1
    pywikibot.output(u"Creating claim in item %s" % datapage.title())
    data = pywikibot.query.GetData(params, datapage.site())
    if 'error' in data:
        #raise RuntimeError("API query error: %s" % data)
        logging.warning("API query error: %s" % data )
        print "API query error: %s" % data
        return
    if 'warnings' in data:
        warning(str(data[u'warnings']))
    guid=data['claim']['id'] if 'claim' in data else ''
    refhash = ''
        
    editRefs(datapage, lang, guid, refhash, refs={('P143', wikiDataPage[lang]),})   
    logging.info('[[%s]]: added coordinates' % (article) )

    time.sleep(4)
    return True

def editRefs(datapage, lang, guid, refhash='', refs=None): 
        botflag = True
   
        if refs:
            snak = []
            if isinstance(refs, dict):
                # the references must be like this:
                # {"p?": [{"snaktype": "value", 
                #          "property":"p?",
                #          "datavalue": {u'type': u'string', u'value': u'...'}},
                #         {"snaktype": "value", ... }}, ]}
                pass
            elif isinstance(refs, set):
                # the references must be like this:
                # {(ref1, value1), (ref2, value2)}
                for ref in refs:
                    if isinstance(ref, basestring):
                        raise RuntimeError(
                            "the references must be like this: {(ref1, value1), (ref2, value2)}")
                    for i in range(2):
                        if isinstance(ref[i], int):
                            value = ref[i]
                        elif isinstance(ref[i], basestring):
                            try:
                                value = int(ref[i])
                            except ValueError:
                                try:
                                    value = int(
                                        ref[i].lower().replace("Q",
                                                               "").replace("P", ""))
                                except ValueError:
                                    if i == 0:
                                        typesearch = 'property'
                                    else:
                                        typesearch = 'item'
                                    #lang=datapage._originSite.lang
                                    search=datapage.searchentities(
                                        ref[i], typesearch,
                                        lang=lang)
                                    #print search
                                    value = int(
                                        search[0]["id"].replace("Q",
                                                                "").replace("P",
                                                                            ""))
                                else:
                                    pass
                            else:
                                pass
                        else:
                            raise RuntimeError("Unknown item: %s" % ref[i])
                        snak.append(value)
            else:
                raise RuntimeError(
                    "the references format cannot be understood!")
            if snak:
                finalsnak = {}
                for i in range(0, len(snak) / 2):
                    snaki = [
                        {"snaktype": "value",
                         "property":"P"+str(snak[i*2]),
                         "datavalue": {"type": "wikibase-entityid",
                                       "value": {"entity-type": "item",
                                                 "numeric-id": snak[(i * 2) + 1]}}}]
                    finalsnak["P%d" % snak[i * 2]] = snaki
            else:
                finalsnak=refs
            finalsnak=pywikibot.json.dumps(finalsnak)
            finalsnak=finalsnak.replace("'", '"')
            params = {
            'action': 'wbsetreference',
            'statement': guid,
            'snaks': u"%s" % finalsnak,
            }
            params['token'] = datapage.site().getToken()
            if refhash:
                params['reference'] = refhash
            if botflag:
                params['bot'] = 1
            pywikibot.output(u"Adding references to claim in %s" % datapage.title())
            
            data = pywikibot.query.GetData(params, datapage.site())
            if 'error' in data:
                logging.warning("API query error: %s" % data)
                raise RuntimeError("API query error: %s" % data)
            if (u'warnings' in data) and \
               (not data[u'warnings'][u'messages'][u'0'][u'name'] == u'edit-no-change'):
                warning(str(data[u'warnings']))


def getCoordinates(cursor, lang):

    coordTable = 'u_dispenser_p.coord_' + lang + 'wiki'

    query = """SELECT /* SLOW_OK */ page_title, ips_item_id, gc_lat, gc_lon 
                    FROM page
                    JOIN %s ON gc_from=page_id
                    LEFT JOIN u_kentaur_p.wb_items_per_site ON ips_site_id = '%swiki' AND ips_site_page_norm = page_title
                    WHERE (page_namespace=0 AND (gc_globe = '' OR gc_globe = 'Earth') AND gc_primary = 1 )
                    ORDER BY page_title""" 
    # AND  STRCMP('Ba', page_title) < 0
    cursor.execute(query % (coordTable, lang))
    if DEBUG:
        print query % (coordTable, lang)

    return cursor


##################
### main

lang = 'de'
logfile = '/home/kentaur/py/wikidata/ghel_add_%s.log' % lang

logging.basicConfig(filename=logfile ,level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s %(message)s')

site = pywikibot.Site(lang, "wikipedia")

connCoord = None
cursorCoord = None
    
(connCoord, cursorCoord) = connectCoordDb(lang)
results = getCoordinates(cursorCoord, lang)

logging.info(u'%s: has %s coordinates in total.' % (lang, results.rowcount) )

addedCount = 0
pageCoordCount = 1
pageTitle = u''
prevTitle = u''
prevPageId = None
prevLat = None
prevLon = None

for (pageTitle, dataPageId, lat, lon) in results:
            
    pageTitle = unicode(pageTitle, "utf-8")
    
    if prevTitle == pageTitle:
        pageCoordCount += 1
    elif prevTitle:
        if pageCoordCount == 1:
            if checkCoordinates(prevTitle, prevPageId, prevLat, prevLon, cursorCoord):
                addedCount += 1
        else:
            logging.info(u'[[%s]]: has %s coordinates.' % (prevTitle, pageCoordCount) )
        pageCoordCount = 1

    prevTitle = pageTitle
    prevPageId = dataPageId
    prevLat = lat
    prevLon = lon

if pageCoordCount == 1 and prevTitle:
    if checkCoordinates(prevTitle, prevPageId, prevLat, prevLon, cursorCoord):
        addedCount += 1

logging.info(u'%s: added coordinates to %s Wikidata pages.' % (lang, addedCount) )
