# DISTRIBUTED SYSTEMS | Final project | Anette Sarivuo | 0544022

import sys # for catching errors
import threading # for performing multiple tasks at once
from collections import deque # for double ended queue needed in iterating thru Wiki pages
from xmlrpc.server import SimpleXMLRPCServer # for building the XML RPC server
import xml.etree.ElementTree as ET # for parsing the database (XML-file)
import requests # for HTTP requests (Wikipedia application programming interface)
import time # for timestamps

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
     
    # getWikiURL: Function for getting the wikipedia article link
    def getWikiURL(searchTerm):
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
        # get wikiPageUrl out: It's the first item in the last array of dataSet
        wikiPageUrl = dataSet[-1][0]
        return wikiPageUrl
     
        
    def wikiLinksRequest(searchTerm):         
        #### SET UP REQUESTS FOR WIKIPEDIA OPENSEARCH ####
        # one request per searchTerm
        S = requests.Session()
        URL = "https://en.wikipedia.org/w/api.php"
        links = []
        PARAMS = {
            "action": "query",
            "format": "json",
            "prop": "links",
            "titles": searchTerm
        }
        # Get response R:
        DATA = S.get(url=URL, params=PARAMS).json()
        ARTICLES = DATA["query"]["pages"]
        
        for i, j in ARTICLES.items():
            for k in j["links"]:
                title = k["title"]
                links.append(title) 
                
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
        global path
        global resultPath
        global deQueue
        
        for link in links:
            if (link in aTo):
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
        
        while (len(deQueue) != 0):
            # as long as there are items in the queue, get wiki links of the next item
            searchTerm = deQueue.popleft()
            linkThread = threading.Thread(target=getWikiLinks, args=(searchTerm, aTo))
            linkThread.start()
            linkThread.join() # Tell other threads to wait for this article check to finish
    
    def precheckArticles(aFrom, aTo):
        # CHECK THE NUMBER OF LINKS IN THE START ARTICLE
        aLinks = wikiLinksRequest(aFrom)
        
        if (len(aLinks) == 0):
            print("The start page does not contain any links!")
            return False
       
        # IF THE START PAGE IS NO DEAD END:
        return True

    def transformSearchTermIntoTitle(aFrom, aTo):
        i = 0
        newTitles = []
        for article in [aFrom, aTo]:
            article = getWikiURL(article) # in URL form
            print(article)
            splitList = article.split("/") # https://en.wikipedia.org/wiki/Compartmental_models_in_epidemiology
            newTitles.append(splitList[-1])
            i += 1
        aFrom = newTitles[0]
        aTo = newTitles[1]
        return aFrom, aTo
    
    # pathfinder:
    # A function that handles the path finding on the server side.
    # Receives user-given parameters from the client.
    # Calls other functions to go through the Wiki articles and find the
    # optimal route between the two.
    # Returns the results.
    def pathfinder(aFrom, aTo, aTime):
        # Transform the input titles into proper titles:
        aFrom, aTo = transformSearchTermIntoTitle(aFrom, aTo)
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