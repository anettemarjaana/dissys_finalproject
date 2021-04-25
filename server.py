# DISTRIBUTED SYSTEMS | Final project | Anette Sarivuo | 0544022

import sys # for catching errors
import threading # for performing multiple tasks at once
from collections import deque # for double ended queue needed in iterating thru Wiki pages
from xmlrpc.server import SimpleXMLRPCServer # for building the XML RPC server
import requests # for HTTP requests (Wikipedia application programming interface)
import time # for timestamps
from pprint import pprint # for json object prints

path = {}
resultPath = {}
deQueue = deque() 

# GOAL OF THE SERVER: allow clients to search articles on Wikipedia API
# and find the shortest path between 2 given articles.
# List the connecting articles to the client.

# DEFINING SERVER
with SimpleXMLRPCServer(('localhost', 3000)) as server:
    server.register_introspection_functions()
    
    #### CREATE NECESSARY FUNCTIONS  ####
     
    # getWikiTitle: Function for getting the wikipedia article title
    def getWikiTitle(searchTerm):
         #### SET UP REQUESTS FOR WIKIPEDIA OPENSEARCH ####
        S = requests.Session()
        URL = "https://en.wikipedia.org/w/api.php"
        # Let the user define the search term:
        PARAMS = {
            "action": "opensearch",
            "format": "json",
            "namespace": "0",
            "limit": "1",
            "search": searchTerm
        }
        # Make the query in the Wiki API
        dataSet = S.get(url=URL, params=PARAMS).json()      
        # get wikiPageUrl out: It's the first item in the second array of DATA
        
        if (dataSet[1]):
            wikiTitle = dataSet[1][0]
            print("Wiki title: %s" % wikiTitle)
        else:
            wikiTitle = ""
        
        return wikiTitle
     
        
    def wikiLinksRequest(searchTerm):        
        # The time it takes for the wiki link request of one article
        # is being measured in order to avoid the program getting stuck
        # at checking one article. It should not take longer than max
        # 40 seconds per article
        searchStart = time.time()
        #### SET UP REQUESTS FOR WIKIPEDIA OPENSEARCH ####
        # one request per searchTerm
        S = requests.Session()
        URL = "https://en.wikipedia.org/w/api.php"
        links = []
        PARAMS = { # prop: extlinks for external links
            "action": "query",
            "format": "json",
            "prop": "links",
            "pllimit": "max",
            "titles": searchTerm
        }
        # Get response R:
        DATA = S.get(url=URL, params=PARAMS).json()
        ARTICLES = DATA["query"]["pages"]
    
        for i, j in ARTICLES.items():
            try:
                for link in j["links"]:
                    loopTime = time.time()
                    if ((loopTime - searchStart) > 40):
                        print(" ### 40 s has passed on request of searchterm: %s. Quitting wikiLinksRequest. ### " % searchTerm)
                        return links
                    title = link["title"]
                    links.append(title) 
            except KeyError as error:
                # links can not be found in the article object
                pass
        

        # If there are more than 500 links in the article, the query
        # returns "continue" key. Let's keep making new requests
        # until the key is not returned anymore:
        while ("continue" in DATA):
            plcontinue = DATA["continue"]["plcontinue"]
            PARAMS["plcontinue"] = plcontinue
            
            DATA = S.get(url=URL, params=PARAMS).json()
            ARTICLES = DATA["query"]["pages"]
            
            for i, j in ARTICLES.items():
                try:
                    for link in j["links"]:
                        loopTime = time.time()
                        if ((loopTime - searchStart) > 60):
                            print(" ### 40 s has passed on request of searchterm: %s. Quitting wikiLinksRequest. ### " % searchTerm)
                            return links
                        title = link["title"]
                        links.append(title) 
                except KeyError as error:
                    # Can not find "links" ob in the article object
                    pass
           
        return links


    # A function for handling links on a specific page
    def handleWikiLinks(searchTerm, aTo, links):        
        # The time it takes for the links handling of one article
        # is being measured in order to avoid the program getting stuck
        # at checking one article. It should not take longer than max
        # 40 seconds per article
        searchStart = time.time() 
        global path
        global resultPath
        global deQueue
        
        # Logic of this loop is from: https://github.com/stong1108/WikiRacer/blob/master/wikiracer.py 
        if (len(links) > 0):
            for link in links:
                loopTime = time.time()
                if ((loopTime - searchStart) > 40):
                    print(" ### 40 s has passed on request of searchterm: %s. Quitting handleWikiLinks. ### " % searchTerm)
                    break
                if (link == aTo):
                    # If the link is the "end article" of the path:
                    # empty the list of articles to check
                    deQueue = deque() 
                    # resultPath is the path to be returned
                    resultPath = path[searchTerm] + [link]
                    # empty temporary path list
                    path = {}
                    print("aTo was reached!")
                    break
                if (link not in path) and (link != searchTerm):
                # If not, check if this link is already in the path.
                # If it's not ---> add it on queue to be checked
                    path[link] = path[searchTerm] + [link]
                    deQueue.append(link)

    # getWikiLinks:
    # A function for getting all links in a wiki article with a search term.
    # It is ran in a thread and also starts a thread.
    def getWikiLinks(searchTerm, aTo):
        # Request links of the specific Wiki article:
        links = wikiLinksRequest(searchTerm)
        # Handle the links of the article:
        handleThread = threading.Thread(target=handleWikiLinks, args=(searchTerm, aTo, links))
        handleThread.start()
        handleThread.join()
        # once finished, return to findShortestPath to fetch another article
        # in the queue to check

    
    # findShortestPath:
    # MAIN WORKER UNIT
    # A function for iterating through the Wikipedia articles and finding the
    # shortest path between two articles. 
    
    # The algorithm in the search is breadth-first search: the program
    # explores paths by going down one level at a time: it starts from
    # observing all children links of the starting page, then looks at each
    # child's links, and so on.
    # Because it does the search one level at a time, it finds the shortest
    # path. The processing might be slow due to many child nodes.
    
    # The function starts a thread for each article title that is being observed.
    # The thread runs getWikiLinks function, which then again starts a new
    # thread for handling those links on the observed article page.
    
    # path is a temporary list of titles between the start and end articles,
    # resultPath is the one that indicates the final path.
    def findShortestPath(aFrom, aTo, aTime):  
        global resultPath
        global path
        global deQueue
        
        resultPath = {} # make sure the resultpath is empty when started
        path[aFrom] = [aFrom]
        # deQueue = a double ended queue for iterating through the Wiki pages.
        # starts with the aFrom item
        deQueue.append(aFrom)
        searchStart = time.time()
        
        while (len(deQueue) != 0):
            # as long as there are items in the queue, get wiki links of the next item
            searchTerm = deQueue.popleft()
            linkThread = threading.Thread(target=getWikiLinks, args=(searchTerm, aTo))
            linkThread.start()
            loopTime = time.time()
            if ((loopTime - searchStart) > 420):
                linkThread.join()
                print(" ### Seven minutes of search has passed. Quitting. ### ")
                break
             
            # If the link thread is dead, return it finished.
            if (not linkThread.is_alive()):
                print("Link thread dead. Returning.")
                linkThread.handled = True
                
            # Tell other threads to wait for this article check to finish.
             # One article link thread can only take max 30 seconds.
            linkThread.join(30)
            
        
        if (len(resultPath) > 1):
            # Check how long it took to search the path:
            bTime = time.time()
            c = bTime - aTime
            # add the execution time in the resultPath set
            resultPath.append(c)
            
            print("\nPath was found!\n")
            for i in resultPath:
                print("> %s" % i)
                
        else:
            # empty article queue and path
            deQueue = deque() 
            path = {}
            # print result on server and client
            noneFound = "No path found"
            print(noneFound)
            resultPath = noneFound
            
    
    def precheckArticles(aFrom, aTo):
        # CHECK THAT BOTH SEARCH TERMS RESULTED IN A VALID WIKI ARTICLE
        if (len(aFrom) < 1 or len(aTo) < 1):
            return False
        
        else: # if lengths of both titles are >= 1:
            # CHECK THE NUMBER OF LINKS IN THE START ARTICLE
            aLinks = wikiLinksRequest(aFrom)
            
            if (len(aLinks) == 0):
                print("The start page does not contain any links!")
                return False
           
            # IF THE START PAGE IS NO DEAD END:
            return True
    
        
    # pathfinder:
    # A function that handles the path finding on the server side.
    # Receives user-given parameters from the client.
    # Calls other functions to go through the Wiki articles and find the
    # optimal route between the two.
    # Returns the results.
    def pathfinder(aFrom, aTo, aTime):
        global resultPath
        # Transform the input titles into proper titles:
        print("\n### New search! ###")
        aFrom = getWikiTitle(aFrom)
        aTo = getWikiTitle(aTo)
        # Check that the articles are valid for route search:
        if (precheckArticles(aFrom, aTo)):
            print("\nGiven start and end articles are valid.\n>>> STARTING PATH SEARCHING >>>\n")
            
            findShortestPath(aFrom, aTo, aTime)
            return resultPath
            
        else:
            return "No valid Wiki article found with this search term!"
    
    #### REGISTER FUNCTIONS ####
    server.register_function(pathfinder)
    

     #### SET THE SERVER TO LISTEN ####
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, exiting.")
        sys.exit(0)