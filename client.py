# DISTRIBUTED SYSTEMS | Final project | Anette Sarivuo | 0544022

import sys # for catching errors
from xmlrpc.client import ServerProxy # for allowing clients to join the XML RCP server
import time # for timestamps
import winsound # for making a sound on Windows when the path has been printed

 #### CONNECTING CLIENTS ####    with server through a proxy:
s = ServerProxy("http://localhost:3000")

if __name__ == "__main__":
    instructions = "\n1) Find the shortest path between two Wikipedia articles\n0) Exit"
    print("\nWelcome to the WikiPathFinder App!"+instructions)
    userInput = "-1" # initialize userInput value
    
    try:
        #### HELPFUL FUNCTIONS ####        
        def checkIfInteger(inputValue):   
            try:
               inputValue = int(inputValue)
            except ValueError:
                print("Invalid input! Enter an integer next time.")
                inputValue = -1
            return inputValue
                
    
        #### LOOP THROUGH USER INPUTS ####
        # if the input is 0, client session ends
        
        while (userInput != "0"):
            userInput = input("\nEnter: ")
            
            if (userInput == "1"):
                ##### FIND THE SHORTEST PATH ####
                print("\n--- Find the shortest path between two Wikipedia articles ---")
                aFrom = input("From: ")
                aTo = input("To: ")
                
                if (len(aFrom) < 1 or len(aTo) < 1):
                    print("Invalid input! Enter a valid article.")
                else:
                    aTime = time.time()
                    # sound specs:
                    duration = 1000
                    freq = 440
                    # Bring these to the server. Search the path on server.py
                    try:
                        resultPath = s.pathfinder(aFrom, aTo, aTime)
                        
                        # resultPath is just a string if no path found:
                        if (isinstance(resultPath, str)):
                            print(resultPath)
                        else:
                            links = len(resultPath)-1
                            c = resultPath.pop()
                            # Parse and print the result here
                            print("\n--- Path length: %s ---" % links)
                            for i in resultPath:
                                print("> %s" % i)
                            print("--- Time it took in seconds: %s ---" % round(c, 2))
                                  
                        # Make a sound when resultPath has been found!
                        winsound.Beep(freq, duration)
                    except KeyboardInterrupt: # not working now, no response
                        print("\nBye bye client!")
                        sys.exit(0)
                
                print(instructions)
                
            elif (userInput == "0"):
                print("Thx bye!")
                
            else:
                print("Invalid input! Enter an integer (0 or 1)")
    
    except KeyboardInterrupt:
        print("\nBye bye client!")
        sys.exit(0)