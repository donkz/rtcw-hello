# -*- coding: utf-8 -*-
"""
Created on Mon Nov 30 01:08:44 2020

@author: donkz
Big credit to PyQuake3
"""
import os

from bs4 import BeautifulSoup
from bs4 import Tag

import re as RE
import socket as SO
import traceback
import sys
from pathlib import Path
import logging

servers = {"LOCAL" : ['127.0.0.1', 27960], "LOCALEC2" : ['172.31.85.10', 27960],"RTCWPro" : ['34.235.224.222', 27960], "OSP" : ['34.235.224.222', 27961], "TK" : ['74.91.116.89', 27960]}
serverkey = "RTCWPro"
modfolder = "rtcwpro"
mainfolder = "main" #windows is not case sentitive, but linux is
essential_fields = ["version","gamename","mapname","timelimit"]

output_file_path = r'/var/www/html/index.html'
game_path = r"/home/rtcwserver/serverfiles/" #linux
if sys.platform == "linux" or sys.platform == "linux2":
    print("[ ] Linux platform properties")
elif sys.platform == "win32":
    game_path = r"D:\Games\Return to Castle Wolfenstein\\" #windows
    output_file_path = "index.html"
    print("[ ] Windows platform properties")



data_folder = Path(game_path)

main_exceptions = [
         'mp_pak0.pk3',
         'mp_pak01.pk3',
         'mp_pak1.pk3',
         'mp_pak2.pk3',
         'mp_pak3.pk3',
         'mp_pak4.pk3',
         'mp_pak5.pk3',
         'sp_pak1.pk3',
         'sp_pak2.pk3',
         'sp_pak3.pk3',
         'mp_pakmaps0.pk3',
         'mp_pakmaps1.pk3',
         'mp_pakmaps2.pk3',
         'mp_pakmaps3.pk3',
         'mp_pakmaps4.pk3',
         'mp_pakmaps5.pk3',
         'mp_pakmaps6.pk3',
         'sp_rend2_shaders0.pk3',
         'mp_bin.pk3',
         'mp_bin0.pk3',
         'pak0.pk3'
 ]

folder_exceptions = []




logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Response messages
WELCOME_MESSAGE = "Hi, welcome to wolf server!"
HELP_MESSAGE = "You can ask me to check osp... or shrub"
HELP_REPROMPT = "What can I help you with?"
FALLBACK_MESSAGE = "I can't help you with that. It can help you to check OSP or check shrub",
FALLBACK_REPROMPT = "What can I help you with"
ERROR_MESSAGE = "Sorry, an error occurred."
STOP_MESSAGE = "Ok Bye"



def get_server_info(server_name):
    logger.debug("Getting " + server_name + " server status")
    #report = get_report("OSP", '34.235.224.222', 27960)
    #report = get_report('Shrub', '104.194.9.163', 27960)
    report = get_report(server_name, servers[server_name][0], servers[server_name][1])
    return report

def list_servers():
    server_list = "Available servers are " + ", ".join(servers)
    return server_list

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class ConnectionError(Error):
    """Error in network connection or protocol."""
    pass

class Connection(object):
    """
    Low level connection to a Quake 3 server. Note that we
    bridge two levels of abstraction here, networking and
    Quake 3 packet format. But who cares? :-D

    The trickiest part here is managing responses from the
    server as some commands generate multiple UDP packets!
    Check out receive_all() below for details.
    """

    PREFIX_LENGTH = 4
    PACKET_PREFIX = b"\xff" * PREFIX_LENGTH

    def __init__(self, host, port, size=8192, timeout=1.0, retries=5):
        """
        Create a pseudo-connection to "host" and "port"; we
        try to give UDP communication a semblance of sanity.

        The internal UDP packet buffer will be "size" bytes,
        we'll wait "timeout" seconds for each response, and
        we'll retry commands "retries" times before failing.
        """
        # we neither want to deal with blocking nor with
        # timeouts that are plain silly in 2009...
        assert 0.1 <= timeout <= 4.0
        assert 4096 <= size <= 65536
        assert 1 <= retries <= 10
        self.socket = SO.socket(SO.AF_INET, SO.SOCK_DGRAM)
        # for SOCK_DGRAM connect() slips a default address
        # into each datagram; furthermore only data from the
        # "connected" address is delivered back; pretty neat
        self.socket.connect((host, port))
        self.socket.settimeout(timeout)
        self.host = host
        self.port = port
        self.size = size
        self.timeout = timeout
        self.retries = retries

    def send(self, data):
        """
        Send given data as a properly formatted packet.
        """
        #self.socket.send("%s%s\n" % (Connection.PACKET_PREFIX, data))
        #cmd_string = Connection.PACKET_PREFIX + data + "\n"
        self.socket.send(b'\xFF\xFF\xFF\xFF\x67\x65\x74\x73\x74\x61\x74\x75\x73\x10') #yyyygetstatus

    def receive(self):
        """
        Receive a properly formatted packet and return the
        unpacked (type, data) response pair. Note that one
        packet will be read, not multiple; use receive_all
        to get all packets up to a timeout.
        """
        packet = self.socket.recv(self.size)
        
        if packet.find(Connection.PACKET_PREFIX) != 0:
            raise ConnectionError("Malformed packet")

        first_line_length = packet.find(b"\n")
        if first_line_length == -1:
            raise ConnectionError("Malformed packet")

        response_type = packet[Connection.PREFIX_LENGTH:first_line_length]
        response_data = packet[first_line_length+1:]

        return (response_type, response_data)

    def receive_all(self):
        """
        Receive a sequence of packets until a timeout
        exception. Check that all packets share a type,
        if so merge the data from all packets. Return
        the merged (type, data) response pair.
        """
        packets = []

        try:
            while True:
                packet = self.receive()
                packets.append(packet)
        except SO.timeout:
            # we timed out, so we'll assume that the
            # sequence of packets has ended; not sure
            # if this is a good idea...
            pass
        except:
            print("Nope")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback,
            limit=4, file=sys.stdout)

        assert len(packets) > 0
        status, data = packets[0]
        for packet in packets[1:]:
            assert status == packet[0]
            data += packet[1]

        return (status, data)

    def command(self, cmd):
        """
        Execute given command and return (type, data)
        response pair. Commands will be retried for a
        number of times. (All response packets will be
        read and merged using receive_all.)
        """
        retries = self.retries
        response = None
        while retries > 0:
            self.send(cmd)
            try:
                response = self.receive_all()
            except Exception:
                # TODO: really catch Exception here? no
                # SO.error or something?
                retries -= 1
            else:
                return response
        raise ConnectionError("No response after %d attempts." % self.retries)

    def close(self):
        """Close connection."""
        #print("closing")
        #print(self.socket)
        self.socket.close()

class REs(object):
    """
    A container for regular expressions used to parse the
    result of certain well-known server commands. In best
    Perl tradition, they are totally unreadable. 8-O
    """
    # parse a player line from "getstatus" command
    # 11 50 "|ALPHA|MarvinTheSpud"
    GETSTATUS = RE.compile(r'^(-?)(\d+) (\d+) "(.*)"')
    # parse a player line from "rcon status" command
    # 2 0 70 |ALPHA| Mad Professor^7 0 127.0.0.1:35107 229 25000
    RCON_STATUS = RE.compile(r'\s*(\d+)\s+(-?)(\d+)\s+(\d+)\s+(.*)\^7\s+(\d+)\s+(\S*)\s+(\d+)\s+(\d+)')

class Player(object):
    """Record collecting information about a player."""

    def __init__(self):
        """Create empty record with lots of None fields."""
        # information from getstatus request
        self.frags = None
        self.ping = None
        self.name = None
        # information from rcon status request
        self.address = None
        self.slot = None
        self.lastmsg = None
        self.qport = None
        self.rate = None
        # information from dumpuser request
        self.guid = None
        self.variables = None

    def __str__(self):
        """Short summary of name, address, and guid."""
        return ("Player<name: %s; address: %s; guid: %s>" %
            (self.name, self.address, self.guid))

class Server(object):
    """Record collecting information about a server."""

    def __init__(self, filter_colors=True):
        """Create empty record with lots of None fields."""
        # meta information before connect
        self.filter = filter_colors
        self.host = None
        self.port = None
        # shortcuts to well-known variables
        self.name = None
        self.game = None
        self.map = None
        self.protocol = None
        self.version = None
        # dict of *all* server variables
        self.variables = {}
        # list of players
        self.players = []

    def address(self):
        """Helper to get "ip:port" for a server."""
        return "%s:%s" % (self.host, self.port)

    def get_address(self):
        """Compatibiltiy alias for address()."""
        return self.address()

    def command(self, command):
        """Wrapper calling Connection.command() for a server."""
        return self.connection.command(command)

    def filter_name(self, name):
        """Helper to remove Quake 3 color codes from player names."""
        result = ""
        i = 0
        while i < len(name):
            if name[i] == "^":
                i += 2
            else:
                result += name[i]
                i += 1
        return result

    def __str__(self):
        """Short summary of name, address, and map."""
        return ("Server<name: %s; address: %s; map: %s>" %
            (self.name, self.address(), self.map))

class Parser(object):
    """
    Mixin class to parse various server responses into
    useful information. Should be applied to subclasses
    of Server.
    """
    def parse_getstatus_variables(self, data):
        """
        Parse variables portion of getstatus response.
        The format is "\\key\\value\\key\\value..." and
        we turn that into a dictionary; selected values
        are also made fields.
        """
        data = data.split("\\")[1:]
        assert len(data) % 2 == 0
        keys = data[0::2]
        values = data[1::2]
        self.variables = dict(zip(keys, values))

        if self.filter:
            self.name = self.filter_name(self.variables["sv_hostname"])
        else:
            self.name = self.variables["sv_hostname"]

        self.game = self.variables["gamename"]
        self.map = self.variables["mapname"]
        self.protocol = self.variables["protocol"]
        self.version = self.variables["version"]

    def parse_getstatus_players(self, data):
        """
        Parse players portion of getstatus response.
        TODO
        """
        assert len(data) > 0
        self.players = []

        for record in data:

            match = REs.GETSTATUS.match(record)
            if match:
                negative, frags, ping, name = match.groups()
                if negative == "-":
                    frags = "-" + frags
                if self.filter:
                    name = self.filter_name(name)

                player = Player()
                player.frags = int(frags)
                player.ping = int(ping)
                player.name = name
                self.players.append(player)

    def parse_getstatus(self, data):
        """
        Parse server response to getstatus command. The
        first line of the response has lots of variables
        while the following lines have players.
        """
        data = data.strip().split("\n")

        variables = data[0].strip()
        players = data[1:]

        self.parse_getstatus_variables(variables)

        if len(players) > 0:
            self.parse_getstatus_players(players)

    def getstatus(self):
        """
        Basic server query for public information only.
        """
        status, data = self.connection.command("getstatus")
        if status == "statusResponse":
            self.parse_getstatus(data)

    def update(self):
        """
        Compatibiltiy alias for getstatus().
        """
        self.getstatus()

    def parse_rcon_status_players(self, data):
        """
        Parse players portion of RCON status response.
        TODO
        """
        assert len(data) > 0
        self.players = []

        for record in data:

            match = REs.RCON_STATUS.match(record)
            if match:
                slot, negative, frags, ping, name, lastmsg, address, qport, rate = match.groups()
                if negative == "-":
                    frags = "-" + frags
                if self.filter:
                    name = self.filter_name(name)

                player = Player()
                player.slot = int(slot)
                player.frags = int(frags)
                player.ping = int(ping)
                player.name = name
                player.lastmsg = int(lastmsg)
                player.address = address
                player.qport = int(qport)
                player.rate = int(rate)
                self.players.append(player)

    def parse_rcon_status(self, data):
        """
        Parse RCON status response. There are at least
        three lines, the first is "map: bla" so we can
        get an updated map variable. The next two are
        the table header, all remaining ones (if any)
        are players, one player on each line.
        """
        data = data.strip().split("\n")
        mapname = data[0].strip().split(": ")[1].strip()

        self.variables["mapname"] = mapname
        self.map = mapname

        players = data[3:]
        if len(players) > 0:
            self.parse_rcon_status_players(players)

    def rcon_status(self):
        """
        TODO
        """
        status, data = self.rcon_command("status")
        if status == "print" and data.startswith("map"):
            self.parse_rcon_status(data)

    def rcon_update(self):
        """
        Compatibiltiy alias for rcon_status().
        """
        self.rcon_status()

    def parse_dumpuser(self, player, data):
        """
        Two header lines followed by "key value" lines
        separated by (lots of) spaces; spaces in values
        are present too, so we split at most once.
        TODO
        """
        data = data.strip().split("\n")[2:]
        variables = {}
        for record in data:
            # we split at most once to not lose spaces
            # inside a value (a name for example)
            separated = record.strip().split(None, 1)
            key = separated[0].strip()
            value = separated[1].strip()
            variables[key] = value

        # we need to avoid updating one player with
        # information for another, so we check for
        # some equalities before we believe the new
        # data to apply
        if player.address == variables["ip"] and player.rate == int(variables["rate"]):
            # alright, update the player object with new information
            player.variables = variables
            player.guid = variables["cl_guid"]

    def rcon_dumpuser_all(self):
        """
        TODO
        """
        for player in self.players:
            status, data = self.rcon_command("dumpuser %d" % player.slot)
            assert status == "print" and data.startswith("userinfo")
            self.parse_dumpuser(player, data)

class Guest(Server, Parser):
    """
    Server implementation that cannot perform any RCON
    commands. The right class if you are browsing some
    random servers.
    """
    def __init__(self, host, port, filter_colors=True):
        """
        TODO
        """
        Server.__init__(self, filter_colors)
        self.connection = Connection(host, port)
        self.host = host
        self.port = port

class Administrator(Server, Parser):
    """
    Server implementation that can perform any command
    an administrator can. The right class if you're in
    the business of writing admin interfaces.
    """
    def __init__(self, host, port, rcon_password, filter_colors=True):
        """
        TODO
        """
        Server.__init__(self, filter_colors)
        self.connection = Connection(host, port)
        self.host = host
        self.port = port
        self.rcon_password = rcon_password

    def rcon_command(self, command):
        """
        Execute an RCON command through the underlying
        connection and return the (type, data) response
        pair.
        """
        command = "rcon \"%s\" %s" % (self.rcon_password, command)
        status, data = self.connection.command(command)
        # TODO: why make this into an exception? the regular
        # command() method doesn't raise?
        if status.startswith(("Bad rcon", "No rcon")):
            raise ConnectionError(status.strip())
        return (status, data)

def PyQuake3(server, rcon_password=None, filter_colors=True):
    """
    Factory method for some backwards compatibility.
    """
    host, port = server.split(":")
    port = int(port)
    if rcon_password is None:
        return Guest(host, port, filter_colors)
    else:
        return Administrator(host, port, rcon_password, filter_colors)

def test_connection():
    c = Connection('34.235.224.222', 27960)

    status = c.command("getstatus")
    assert len(status) > 0
    print(status)

    #status = c.command("rcon status")
    #assert status[1].startswith("Bad rcon")
    #print(status)

    c.close()

    try:
        print(c.command("getstatus"))
    except SO.error as e:
        assert e is not None
        print(e)

    try:
        d = Connection("74.91.116.89", 27960)
        d.command("getstatus")
    except ConnectionError as e:
        assert e is not None
        print(e)

def test_updates_and_players():
    # put your own server/password here to test
    a = Administrator("34.235.224.222", 27960, "fuckchina")
    a.update()
    for p in a.players:
        print(p)
    a.rcon_update()
    for p in a.players:
        print(p)
    a.rcon_dumpuser_all()
    for p in a.players:
        print(p)

def stripColors(line, colors):
    '''Strip character combinations like ^7don^eN^7ka to doNka'''
    ret = line
    for color in colors:
        ret = ret.replace(color,"")
    return ret;  

def setup_colors():
    colors_arr = []
    for x in range(33,126):
        colors_arr.append("^"+chr(x))
    return colors_arr

def get_report(server_name, server, port):
    debug = False
    c = Connection(server, port)
    status = c.command("getstatus")
    serverinfo = status[1].decode()
    if debug: print(serverinfo)
    serverinfo_split = serverinfo[1:].split("\\")

    
    si_dict = {}
    for i in range(0,int(len(serverinfo_split)/2)):
        si_dict[serverinfo_split[i*2]] = serverinfo_split[i*2+1]
    
    last_elem_split = si_dict[serverinfo_split[len(serverinfo_split)-2]].split("\n")
    si_dict[serverinfo_split[len(serverinfo_split)-2]] = last_elem_split[0]
    if debug: print(si_dict)
    
    allies_no = []
    axis_no = []
    if 'Players_Allies' in si_dict:
        if(si_dict['Players_Allies'] != '(None)'):
            allies_no = list(map(int,si_dict['Players_Allies'].strip().split(" ")))
        else: 
            allies_no = []
        if(si_dict['Players_Axis'] != '(None)'):
            axis_no = list(map(int,si_dict['Players_Axis'].strip().split(" ")))
        else: 
            axis_no = []
        
    players_raw = last_elem_split[1:-1]
    
    colors = setup_colors()
    
    axis_players = {}
    allies_players = {}
    other_players = {}
    for index, player in enumerate(players_raw, start=1):
        player_split = player.split(" ")
        name = stripColors(player_split[2], colors)
        if index in allies_no: 
            allies_players[index] = [name[1:-1], player_split[0], player_split[1]] #[1:-1] to drop quotes
        elif index in axis_no: 
            axis_players[index] = [name[1:-1], player_split[0], player_split[1]]
        else:
            other_players[index] = [name[1:-1], player_split[0], player_split[1]]
            
    
    num_players = str(len(players_raw))
    teams = ""
    if len(other_players) != len(players_raw):
        teams = " " + str(len(allies_players)) + " v " + str(len(axis_players))
    mapname = si_dict['mapname']
    timelimit = si_dict['timelimit'].split(".")[0]
    logger.debug("Finishing up...")
    logger.debug(server_name)
    logger.debug(num_players)
    logger.debug(teams)
    logger.debug(mapname)
    logger.debug(timelimit)
    logger.debug(f'{server_name} has {num_players} total players{teams} playing on {mapname}. Current round timelimit is {timelimit} minutes')
    
    report = "kek"
    if len(players_raw) == 0:
        report = server_name + " is empty"
    else:
        report = f'{server_name} has {num_players} total players{teams} playing on {mapname}. Current round timelimit is {timelimit} minutes'
    logger.debug("Returning this report")
    logger.debug(report)
    return {"reportstring" : report, "serverinfo" : si_dict, "allies" : allies_players, "axis" : axis_players, "specs" : other_players}

style_css = """
    .text {
      font-family: "Courier New", Courier, monospace;
      font-size: 14px;
    }
    .versuslt1 {
      font-weight: bold;
    }
    .versusgt1 {
      font-weight: bold;
    }
    .versuslt2 {
      font-weight: bold;
      color: red;
      font-size: 14px !important;;
    }
    .versusgt2 {
      font-weight: bold;
      color: red;
      font-size: 14px !important;;
    }
    .gold {
      background-color: #D4AF37;
    }
    .silver {
      background-color: #C0C0C0;
    }
    .bronze {
      background-color: #cd7f32;
    }
    .red5 {
      background-color: #F50000;
    }
    .red4 {
      background-color: #ff704d;
    }
    .red3 {
      background-color: #ff9980;
    }
    .red2 {
      background-color: #ffc2b3;
    }
    .red1 {
      background-color: #ffebe6;
    }
    .green5 {
    }
    .green4 {
      background-color: #adffab;
    }
    .green3 {
      background-color: #90ee90;
    }
    .green2 {
      background-color: #82df83;
    }
    .green1 {
      background-color: #65c368;
    }
    .Allies {
      background-color: #BFDAFF;
    }
    .Axis {
      background-color: #FFBFBF;
    }
    .nocount {
      color: darksalmon;
    }
        
    tr:nth-child(even) {background-color: #f2f2f2;}
        
    table.blueTable {
      font-family: "Courier New", Courier, monospace;
      border: 1px solid #14191B;
      background-color: #F3FFFB;
      text-align: center;
      border-collapse: collapse;
      white-space: nowrap;
    }
    .bars {
      width: 13em;
      text-align: left;
    }
    table.blueTable td, table.blueTable th {
      border: 1px solid #AAAAAA;
      padding: 0px 6px;
    }
    table.blueTable tbody td {
      font-size: 12px;
    }
    table.blueTable thead {
      background: #030D14;
      background: -moz-linear-gradient(top, #42494f 0%, #1c252b 66%, #030D14 100%);
      background: -webkit-linear-gradient(top, #42494f 0%, #1c252b 66%, #030D14 100%);
      background: linear-gradient(to bottom, #42494f 0%, #1c252b 66%, #030D14 100%);
      border-bottom: 0px solid #444444;
    }
    table.blueTable thead th {
      font-size: 14px;
      font-weight: bold;
      color: #EFEFEF;
      text-align: center;
      border-left: 4px solid #D0E4F5;
    }
    table.blueTable thead th:first-child {
      border-left: none;
    }
    
    table.blueTable tfoot .links {
      text-align: right;
    }
    table.blueTable tfoot .links a{
      display: inline-block;
      background: #1C6EA4;
      color: #FFFFFF;
      padding: 2px 8px;
      border-radius: 5px;
    }
        
    progress[value]::-webkit-progress-bar {
      background-color: #B1E59F;
      foreground-color: #FF5757;
      border-radius: 2px;
      box-shadow: 0 2px 5px rgba(0, 0, 0, 0.25) inset;
    }
    .ui-tooltip {
        white-space: pre-line;
    	font-size:12;
    	background: #A0A0A0;
    	box-shadow: none;
    	border-style: solid;
    	border-width: 10px 10px 0;
    	z-index: 0;
    }
    """

def list_pk3_files(path, folder):
    print("[ ] Scanning files in " + path)
    path = path + folder
    
    pk3_files = [] # will contain elements like [filepath,date]
    for subdir, dirs, files in os.walk(path):
            for file in files:
                #print os.path.join(subdir, file)
                filepath = subdir + os.sep + file

                if filepath.endswith(".pk3"):
                    file_date_str = filepath.replace(path,"").replace("\\","").replace("/","") #windows, linux
                    pk3_files.append(file_date_str)
    #print(osp_files)
    sorted_pk3_files = sorted(pk3_files)
    return sorted_pk3_files

def make_hmtl (output_file_name, tables, report, essential_fields):
    soup = BeautifulSoup("","lxml")
        
    #<html>
    html = Tag(soup, name = "html")
    
    #<head>
    head = Tag(soup, name = "head")
    
    #css and libraries
    link = Tag(soup, name = "link")
    link["rel"] = "stylesheet"
    link["href"] = "https://ajax.googleapis.com/ajax/libs/jqueryui/1.12.1/themes/smoothness/jquery-ui.css"
    
    #scripts
    script = Tag(soup, name = "script")
    script["src"] = "https://ajax.googleapis.com/ajax/libs/jquery/3.4.1/jquery.min.js"
    #
    script2 = Tag(soup, name = "script")
    script2["src"] = "https://ajax.googleapis.com/ajax/libs/jqueryui/1.12.1/jquery-ui.min.js"
    
    #style
    style = Tag(soup, name = "style")
    
    #meta
    meta = Tag(soup, name = "meta")
    meta["charset"] = "UTF-8"
    
    soup.append(html)
    soup.html.append(head)
    soup.head.append(meta)
    soup.head.append(link)
    soup.head.append(script)
    soup.head.append(script2)
    soup.head.append(style)
    soup.style.append(style_css)
    
    #<body>    
    body = Tag(soup, name = "body")
    soup.html.append(body)
    #soup.body.append(insert_header("RTCW Server details",2))
    servername = report["serverinfo"]["sv_hostname"] if "sv_hostname" in report["serverinfo"] else "this server"
    soup.body.append(insert_header("Welcome to " + servername,2))
    
    serverinfo_lower = {}
    for caps in report["serverinfo"]:
        serverinfo_lower[caps.lower()] = report["serverinfo"][caps]

    essential_fields = [x.lower() for x in essential_fields]
    for e in essential_fields:
        soup.body.append(insert_text(e + " = " + serverinfo_lower[e]))
    
    for header in tables:
        soup.body.append(insert_header(header,3))
        soup.body.append(tables[header])
    
    try:
        html_file = open(output_file_name,"w",encoding="utf-8")
        html_file.write(soup.prettify())
        html_file.close() 
        print("[ ] Wrote html report to " + os.path.abspath(html_file.name))
    except FileNotFoundError as err:
        print("[!] Could not write to " + os.path.abspath(output_file_name) + " Error: ", err)
    except UnicodeEncodeError as err:
        print("[!] Could not encode weird characters in html report " + output_file_name + " Error: ", err)
    except:
        print("[x] Could not write to " + output_file_name + " Unhandled error.")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback,limit=5, file=sys.stdout)
        pass
    
def insert_header(text, size):
    soup = BeautifulSoup("","lxml")
    header1 = Tag(soup, name = "h" + str(size))
    header1["class"] = "header"
    header1.append(text)
    soup.append(header1)
    return soup

def insert_text( content):
    soup = BeautifulSoup("","lxml")
    text = Tag(soup, name = "p")
    text["class"]="text"
    
    text.append(content)
    soup.append(text)
    return soup

def insert_html(content):
    soup = BeautifulSoup("","lxml")
    wrap = Tag(soup, name = "p")
    wrap["class"]="text"
    wrap.append(BeautifulSoup(content, 'html.parser'))
    soup.append(wrap)
    return soup  


def list_to_html(mylist, columns=None, make_links = False, link_loc = "https://s3.amazonaws.com/donkanator.com/rtcw_maps/"):
    columns = ["Files"]
    
    soup = BeautifulSoup("","lxml")        
    table = Tag(soup, name = "table")
    table["class"] = "blueTable"
    #table["id"] = ""
    soup.append(table)
    tr = Tag(soup, name = "tr")
    table.append(tr)
    
    for col in columns:
        th = Tag(soup, name = "th")
        tr.append(th)
        th.append(col)
    for cell in mylist:
        tr = Tag(soup, name = "tr")
        for col in columns:
            td = Tag(soup, name = "td")
            content = cell
            if make_links:
                link = Tag(soup, name = "a")
                link["href"] = link_loc + cell
                link.append(cell)
                content = link
            td.insert(1, content)
            tr.append(td)
            table.append(tr)
    return soup

def teams_to_html(report, columns=None, make_links = True):
    columns = ["#", "Player","Score","Ping"]
    
    soup = BeautifulSoup("","lxml")        
    table = Tag(soup, name = "table")
    table["class"] = "blueTable"
    #table["id"] = ""
    soup.append(table)
    tr = Tag(soup, name = "tr")
    table.append(tr)
    
    teams = ["allies","axis","specs"]
    for col in columns:
        th = Tag(soup, name = "th")
        tr.append(th)
        th.append(col)
    for team in teams:
        if 'Players_Allies' in report['serverinfo'] and 'Players_Axis' in report['serverinfo']:
            tr = Tag(soup, name = "tr")
            th = Tag(soup, name = "th")
            th["colspan"]=2
            th["align"]="left"
            tr.append(th)
            th.append(team)
            table.append(tr)
        else:
            print("[!] No team properties on this server")
        

        for playernum in report[team]:
            tr = Tag(soup, name = "tr")
            td = Tag(soup, name = "td")
            td.append(str(playernum))
            tr.append(td)
            for cell in report[team][playernum]:
                td = Tag(soup, name = "td")
                td.append(str(cell))
                tr.append(td)
                table.append(tr)
    return soup


if __name__ == "__main__":
    main_list = list_pk3_files(game_path, mainfolder)
    folder_list = list_pk3_files(game_path, modfolder)
    
    main_list = list(set(main_list) - set(main_exceptions))
    folder_list = list(set(folder_list) - set(folder_exceptions))
    
    report = get_server_info(serverkey)
    
    main_table = list_to_html(sorted(main_list), make_links=True)
    folder_table = list_to_html(sorted(folder_list), make_links=False)
    player_table = teams_to_html(report)
    
    tables = {}
    tables["Players"] = player_table
    tables[mainfolder + " PK3 Files"] = main_table
    tables[modfolder +" PK3 Files"] = folder_table
    
    make_hmtl(output_file_path,tables, report, essential_fields)