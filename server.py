# DISTRIBUTED SYSTEMS | Final project | Anette Sarivuo | 0544022

import sys # for catching errors
import threading # for performing multiple tasks at once
from collections import deque # for double ended queue needed in iterating thru Wiki pages
from xmlrpc.server import SimpleXMLRPCServer # for building the XML RPC server
import xml.etree.ElementTree as ET # for parsing the database (XML-file)
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
        # get wikiPageUrl out: It's the first item in the first array of DATA
        wikiTitle = dataSet[1][0]
        print("Wiki title: %s" % wikiTitle)
        
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
    
    # getWikiLinks:
    # A function for getting all links in a wiki article with a search term.
    # Is ran in a thread and also starts a thread.
    def getWikiLinks(searchTerm, aTo):
        links = wikiLinksRequest(searchTerm)
        handleThread = threading.Thread(target=handleWikiLinks, args=(searchTerm, aTo, links))
        handleThread.start()
        handleThread.join()

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
    def findShortestPath(aFrom, aTo):        
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
                print(" ### Seven minutes of search has passed. Quitting. ### ")
                break
            linkThread.join() # Tell other threads to wait for this article check to finish
    
    def precheckArticles(aFrom, aTo):
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
        aFrom = getWikiTitle(aFrom)
        aTo = getWikiTitle(aTo)
        # Check that the articles are valid for route search:
        if (precheckArticles(aFrom, aTo)):
            print("\nGiven start and end articles are valid.\n>>> STARTING PATH SEARCHING >>>\n")
            
            findShortestPath(aFrom, aTo)
            
            # Check how long it took to search the path:
            bTime = time.time()
            c = bTime - aTime
            
            if (len(resultPath) != 0):
                print("\nPath was found!")
            else:
                print("\nNo path found!")
                resultPath = "No path found"
            return resultPath, c
        else:
            return "Article failed at pre-check", 0
    
    #### REGISTER FUNCTIONS ####
    server.register_function(pathfinder)
    

     #### SET THE SERVER TO LISTEN ####
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, exiting.")
        sys.exit(0)