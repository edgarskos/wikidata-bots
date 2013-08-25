#!/usr/bin/python
# -*- coding: utf-8  -*-

'''

add new/update "coordinate location" claims for settlements in Estonia

'''


import sys, os
sys.path.append("/home/rk/py/pywikibot/compat")

import time, re
import wikipedia as pywikibot
import pagegenerators
import logging

# output debug messages
DEBUG = False

site = pywikibot.Site("et", "wikipedia")
tpl = pywikibot.Page(site, u'Mall:EestiAsula')

gen = pagegenerators.ReferringPageGenerator(tpl,
                            followRedirects=False,
                            withTemplateInclusion=True,
                            onlyTemplateInclusion=True)
generator = pagegenerators.PreloadingGenerator(gen, pageNumber=10)

claims_rules = {
##### main type deprecated    107: 'q618123', # GDN = geo
    17: 'q191', # Country = Estonia
    
    #TODO: is in the administrative unit
    #TODO: administrative unit type

    #instance of << town Q3957 << alev << alevik << village Q532  
}


def editclaim(article, pid, value):
    if pid and value:
        print 'p%s = %s' % (pid, value)
       
        data.editclaim('p' + str(pid), value,
            raw_value=False,
            refs={('p143', 'q200060'),}, # from Estonian Wikipedia
        )
        logging.info('[[%s]]: modified claim p%s = %s' % (article, pid, value) )
    
        time.sleep(15)


def editcoordinates(datapage, article, theclaim, latitude, longitude):
    assert latitude > 0
    assert longitude > 0
    
    botflag = False
    propertyID = 625 #geo coordinates
    latitudeStr = "%.12f" % (latitude)
    longitudeStr = "%.12f" % (longitude)
    value = "{\"latitude\":"  + latitudeStr  + ",\"longitude\":" + longitudeStr + "}"

    if theclaim:
        params = {
            'action': 'wbsetclaimvalue',
            'claim': theclaim['g'],
            'snaktype': 'value',
            'value': value,
        }
        params['token'] = datapage.site().getToken()
        if botflag:
            params['bot'] = 1
        pywikibot.output(u"Changing claim in item %s" % datapage.title())
        data = pywikibot.query.GetData(params, datapage.site())
        if 'error' in data:
            raise RuntimeError("API query error: %s" % data)
        if (u'warnings' in data) and \
           (not data[u'warnings'][u'messages'][u'0'][u'name'] == u'edit-no-change'):
           warning(str(data[u'warnings']))
        guid=theclaim['g']
        refhash=getreference(datapage, guid)
        editrefs(datapage, guid, refhash, refs={('p143', 'q200060'),}) # from Estonian Wikipedia
        logging.info('[[%s]]: modified coordinates' % (article) )
    else:  
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
            raise RuntimeError("API query error: %s" % data)
        if 'warnings' in data:
            warning(str(data[u'warnings']))
        guid=data['claim']['id'] if 'claim' in data else ''
        refhash = ''
        
        editrefs(datapage, guid, refhash, refs={('p143', 'q200060'),}) # from Estonian Wikipedia  
        logging.info('[[%s]]: added coordinates' % (article) )

    time.sleep(15)

def getreference(datapage, guid, sysop=False):
        """Return first reference hash for claim
        """
        refhash = ''
        params = {
            'action': 'wbgetclaims',
            'claim': guid,
        }
        # retrying loop is done by query.GetData
        data = pywikibot.query.GetData(params, datapage.site(), sysop=sysop)
        
        if 'error' in data:
            raise RuntimeError("API query error: %s" % data)
        if not 'claims' in data:
            raise NoPage(datapage.site(), unicode(datapage),
                         "API query error, no pages found: %s" % data)
        claimInfo = data['claims'].values()[0]
        refhash = claimInfo[0]['references'][0]['hash']
        return refhash
        
        
def editrefs(datapage, guid, refhash='', refs=None): 
        botflag = False
   
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
                                    search=datapage.searchentities(
                                        ref[i], typesearch,
                                        lang=datapage._originSite.lang)
                                    value = int(
                                        search[0]["id"].replace("q",
                                                                "").replace("p",
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
                         "property":"p"+str(snak[i*2]),
                         "datavalue": {"type": "wikibase-entityid",
                                       "value": {"entity-type": "item",
                                                 "numeric-id": snak[(i * 2) + 1]}}}]
                    finalsnak["p%d" % snak[i * 2]] = snaki
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
                raise RuntimeError("API query error: %s" % data)
            if (u'warnings' in data) and \
               (not data[u'warnings'][u'messages'][u'0'][u'name'] == u'edit-no-change'):
                warning(str(data[u'warnings']))

    
### main

logging.basicConfig(filename='add.log',level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s %(message)s')
        
for page in generator:
    print page

    if page.namespace():
        print 'ERROR: NOT AN ARTICLE'
        continue

    data = pywikibot.DataPage(page)

    settlement = ''
    claims_rules[31] = ''
    for cat in page.categories():
        if re.search( ur'\slinnad', cat.title() ) :
            settlement = 'q3957'                      # town
        elif re.search( ur'\salevid', cat.title() ) :
            settlement = 'q3374262'                   # market town
        elif re.search( ur'\salevikud', cat.title() ) :
            settlement = 'q3744870'                   # et:alevik
        elif re.search( ur'\skülad', cat.title() ) :
            settlement = 'q532'                       # village

    if settlement:
        claims_rules[31] = settlement
    else:
        logging.warning('[[%s]]: has no settlement type' % (page.title()) )

    if data.exists():
        item = data.get()
        
        claims = {}
        if 'claims' in item:
            for claim in item['claims']:
                if claim['m'][1] not in claims:
                    claims[claim['m'][1]] = []
                claims[claim['m'][1]].append(claim)
        
        for pid in claims_rules:
            if pid not in claims:
                rules = claims_rules[pid]
                if not issubclass(type(rules), list):
                    rules = [rules,]
                for rule in rules:
                    if issubclass(type(rule), str):
                        editclaim(page.title(), pid, rule)
        
        theclaim = None
        try:
            theclaim = claims[625][0]
            wikidataCoords = theclaim['m'][3]
            if DEBUG:
                print theclaim
        except KeyError:
            # Key is not present
            wikidataCoords = {}

        pageCoords = {}
        pageCoords['lat'] = 0.0;
        pageCoords['lon'] = 0.0;
        for (template, params) in page.templatesWithParams():
            if template == 'EestiAsula':
                for param in params:
                    matchObj = re.match( ur'(lat|lon)_(\w+?)\s*=\s*(\d+)', param )
                    if matchObj:
                        if matchObj.group(2) == 'deg':
                            pageCoords[matchObj.group(1)] += int(matchObj.group(3))
                        elif matchObj.group(2) == 'min':
                            pageCoords[matchObj.group(1)] += float(matchObj.group(3))/60
                        elif matchObj.group(2) == 'sec':
                            pageCoords[matchObj.group(1)] += float(matchObj.group(3))/3600
                continue

        if DEBUG:
            print pageCoords
        
        if len(wikidataCoords):
            wikidatalatStr = "%.12f" % (wikidataCoords['latitude'])
            wikidatalonStr = "%.12f" % (wikidataCoords['longitude'])
        pagelatStr = "%.12f" % (pageCoords['lat'])
        pagelonStr = "%.12f" % (pageCoords['lon'])
        #modify coordinates?
        if (len(wikidataCoords)==0 or wikidatalatStr != pagelatStr 
            or wikidatalonStr != pagelonStr):                

            editcoordinates(data, page.title(), theclaim, pageCoords['lat'], pageCoords['lon'])

    else:
        print 'ERROR: NO DATA PAGE'

