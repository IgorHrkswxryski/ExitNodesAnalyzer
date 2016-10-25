import requests
import tarfile
import os
import sys
import sqlite3
import re
import csv
import argparse
import datetime
from bs4 import BeautifulSoup

def getURL(page):
    """ Get all HREF of a webpage """

    HTMLPage = page
    start_link = HTMLPage.find("a href")
    if start_link == -1:
        return None, 0
    start_quote = HTMLPage.find('"', start_link)
    end_quote = HTMLPage.find('"', start_quote + 1)
    url = HTMLPage[start_quote + 1: end_quote]
    return url, end_quote

def sqliteImport():
    """ Import archived files to sqlite3 DB """

    # Create database
    try:
        print("Creating database")
        conn = sqlite3.connect('exitNodes.db')
        curs = conn.cursor()
    except:
        print("Database already exists")
    # Create table
    try:
        print("Creating table nodes")
        curs.execute("CREATE TABLE nodes (ExitAddress text, UpTime date)")
    except:
        print("Table already exists")
    # Recursively get files
    print("Importing data, take about 10 minutes")
    for root, subFolders, files in os.walk("."):
        for x in files:
            if bool(re.search(r"(\d+-\d+-\d+-\d+-\d+-\d+)", x)):
                with open(os.path.join(root, x), 'r') as fin:
                    # Reading file
                    data = fin.readlines()
                    # Converting into CSV
                    reader = csv.reader(data , delimiter=' ')
                    # Inserting IP and associated date to database
                    for row in reader:
                        if row[0] == 'ExitAddress':
                            ExitAddress = row[1]
                            UpTime = row[2]
                            try:
                                curs.execute("INSERT INTO nodes (ExitAddress, UpTime) values (?, ?)",(ExitAddress, UpTime))
                            except:
                                print("Error inserting")
    conn.commit()

def selectUpTime(IP):
    """ Retrieve the up time range of a TOR exit node """

    ip = IP
    connected = []
    conn = sqlite3.connect('exitNodes.db')
    curs = conn.cursor()
    # Select distinct date and IP
    curs.execute("SELECT DISTINCT * FROM nodes WHERE ExitAddress=(?)", (ip, ))
    rows = curs.fetchall()
    for index, row in enumerate(rows, start=0):
        # Converting date
        date0 = datetime.datetime.strptime(rows[index-1][1], '%Y-%m-%d').date()
        date1 = datetime.datetime.strptime(rows[index][1], '%Y-%m-%d').date()
        # First appear for the IP on TOR
        if index == 0:
            print("First Up Time : "+row[1])
            connected.append(row[1])
        else:
            # If difference betwee two dates == 1, node is UP
            if date1 == (date0 + datetime.timedelta(days=+1)):
                connected.append(date1)
            # If not, node has been disconnected
            else:
                print("Up : ",connected[0], " -> ", connected[len(connected)-1])
                connected = []
        # Lasr appear for the IP on TOR
        if index == len(rows)-1:
            print("Up : ",connected[0], " -> ", connected[len(connected)-1])
            print("Last Up Time : "+row[1])
            connected.append(row[1])

def downloadFiles():
    """ Download all archived files """

    # URL of TOR exit nodes history
    site = 'https://collector.torproject.org/archive/exit-lists/'
    # Request website
    responseHTML = requests.get(site)
    # Store HTML page
    HTMLPage = str(BeautifulSoup(responseHTML.content, "html.parser"))

    while(True):
        archive, n = getURL(HTMLPage)
        HTMLPage = HTMLPage[n:]
        if archive:
            if ("exit" in archive) and not (os.path.exists(archive)):
                print("Downloading file : "+site+archive)
                responseARCHIVE = requests.get(site+archive)
                # Writing archives
                with open(archive, "wb") as code:
                    code.write(responseARCHIVE.content)
                # Extract archives
                with tarfile.open(archive) as f:
                    f.extractall('.')
                # Remove archives
                os.remove(archive)
            else:
                continue
        else:
            break

if __name__ == '__main__':
    """ Main loop """

    # Parsing arguments
    parser = argparse.ArgumentParser(description="Is my IP an exit TOR node? Pass an IP to the python script.")
    parser.add_argument('-i', action="store", dest="IP", type=str, help="Analyse an IP passed as argument")
    parser.add_argument('-s', action="store", dest="setup", help="Must be execute before first analyze")
    args = parser.parse_args()

    if len(sys.argv) < 2:
        parser.print_usage()

    if args.IP:
        selectUpTime(args.IP)

    if args.setup == "setup":
        downloadFiles()
        sqliteImport()
