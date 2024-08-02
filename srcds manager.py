##############################################################################
## MADE BY NOTNHEAVY.                                                       ##
##############################################################################

# This is my first Python script using threads...

# TODO: prerelease support?

import subprocess;
import sys;
import os;
import requests;
import json;
import threading;
import time;
from typing import Any;

TASK_MANAGER_EXIT       = 1;
STATUS_CONTROL_C_EXIT   = 0xC000013A;
SECONDS_BETWEEN_CHECK   = 60.0;

g_bRunUpdate            = True;
g_bUpdating             = False;
g_strSteamCMD           = "";
g_strSteamCMDScript     = "";

##############################################################################
## INF PARSER                                                               ##
##############################################################################

# This is a really, really basic config "parser", but steam.inf isn't a very
# complex file.
class InfParser():
    # Initialize a dictionary field.
    def __init__(self) -> None:
        self.dictionary = { };

    # Load from a steam.inf file.
    def Read(self, path: str) -> None:
        # Validate the path.
        if (not os.path.isfile(path)):
            raise FileNotFoundError(f"Path \"{path}\" is not a valid path.", path);
        if (not os.path.split(path)[1] == "steam.inf"):
            raise FileNotFoundError(f"Path \"{path}\" is not a valid steam.inf path.", path);

        # Read from the file.
        with (open(path, "r")) as file:
            while (len((line := file.readline())) > 0):
                line = line.replace("\r\n", "");
                line = line.replace("\n", "");
                head, tail = line.split("=");
                if (tail.isnumeric()):
                    self.dictionary[head] = int(tail);
                else:
                    self.dictionary[head] = tail;

    # Clear the dictionary.
    def Clear(self) -> None:
        self.dictionary.clear();

    # Used for indexing with the internal dictionary.
    def __getitem__(self, name: str) -> Any:
        value = self.dictionary.get(name);
        if (value == None):
            raise IndexError(f"Could not find key \"{name}\" in InfParser.");
        return value;

##############################################################################
## STEAM UPDATE SCRIPT                                                      ##
##############################################################################

# Invokes the Steam API to check if the designated app ID and version is outdated.
# If so, run the steamcmd script.
def IsAppIDCorrectVersion(appid: int, version: int, srcds: (subprocess.Popen | None) = None) -> bool:
    # Construct the API call parameters.
    global g_bUpdating;
    if (not g_bRunUpdate):
        return True;
    url = "http://api.steampowered.com/ISteamApps/UpToDateCheck/v1";
    params = {
        "appid":    appid,
        "version":  version
    };

    # Initiate a GET request and check if the response is OK (200), 
    # otherwise throw an exception.
    response = requests.get(url, params = params);
    if (response.ok):
        # Deserialize the JSON and confirm the success and up_to_date parameters.
        content = json.loads(response.content);
        if (not content["response"]["success"]):
            print("srcds manager: *WARNING* API REQUEST FAILED, IGNORING UPDATE REQUEST", file = sys.stderr);
        elif (not content["response"]["up_to_date"]):
            # We will force an update in the following scenarios:
            # - We are launching the server on Windows (as -autoupdate is not available)
            # - The server is already running but the game has been updated
            required_version = (content["response"]["required_version"] if ("required_version" in content["response"]) else -1);
            print(f"srcds manager: server requested restart for appID {appid} (current version is {version} while expected version is {required_version})");

            # Find the steamcmd executable and launch the update script.
            if (srcds):
                g_bUpdating = True;
            process = subprocess.Popen([g_strSteamCMD, "+runscript", g_strSteamCMDScript]);
            process.wait();
            g_bUpdating = False;
            return False;
    else:
        response.raise_for_status();
    return True;

##############################################################################
## SERVER THREAD                                                            ##
##############################################################################

def server_thread(process: subprocess.Popen, parser: InfParser, inf: str) -> None:
    global g_strSteamInf;
    while (True):
        # Sleep for SECONDS_BETWEEN_CHECK seconds (defaulted to a minute).
        time.sleep(SECONDS_BETWEEN_CHECK);
        if (process.poll() != None):
            return;

        # Re-read steam.inf and check for an update. If an update occurs,
        # end this thread.
        time = time.strftime("%H:%M:%S", time.localtime());
        print(f"[{time}] srcds manager: Checking for update...");
        parser.Clear();
        parser.Read(inf);
        if (not IsAppIDCorrectVersion(parser["appID"], parser["ServerVersion"], process)):
            return;

##############################################################################
## ENTRY POINT                                                              ##
##############################################################################

def main(argc: int, argv: list[str]) -> int:
    global g_strSteamCMD, g_strSteamCMDScript, g_bUpdating;

    # Check length of arguments string.
    if (argc == 1):
        print("Please run this program with an executable passed through clargs.", file = sys.stderr);
        return 1;

    # Walk through the parameters and find the -game, -steam_dir and -steamcmd_script parameters.
    argv = argv[1:];
    game = "";
    for i, arg in enumerate(argv):
        if (arg == "-game" and i + 1 < argc):
            game = argv[i + 1];
        elif (arg == "-steam_dir" and i + 1 < argc):
            g_strSteamCMD = os.path.join(argv[i + 1], "steamcmd.exe");
        elif (arg == "-steamcmd_script" and i + 1 < argc):
            g_strSteamCMDScript = os.path.abspath(argv[i + 1]);
    
    # Confirm the game, steamcmd and steamcmd script parameters.
    if (len(game) == 0):
        print("Could not find valid -game parameter.", file = sys.stderr);
        return 1;
    elif (not os.path.isfile(g_strSteamCMD)):
        if (len(g_strSteamCMD) == 0):
            print("Could not find valid -steam_dir parameter.", file = sys.stderr);
        else:
            print(f"-steam_dir parameter is invalid (points to incorrect file \"{g_strSteamCMD}\")", file = sys.stderr);
        return 1;
    elif (not os.path.isfile(g_strSteamCMDScript)):
        if (len(g_strSteamCMDScript) == 0):
            print("Could not find valid -steamcmd_script parameter.", file = sys.stderr);
        else:
            print(f"-steamcmd_script parameter is invalid (points to incorrect file \"{g_strSteamCMDScript}\")", file = sys.stderr);
        return 1;

    # Check if the game directory exists with a valid steam.inf file.
    inf = os.path.join(os.path.dirname(os.path.realpath(argv[0])), "tf", "steam.inf");
    if (not os.path.isfile(inf)):
        print(f"Could not find file \"{inf}\"", file = sys.stderr);
        return 1;

    # Create a new InfParser instance and read from steam.inf initially
    # to check for an initial update.
    parser = InfParser();
    parser.Read(inf);
    IsAppIDCorrectVersion(parser["appID"], parser["ServerVersion"]);

    # Launch the process. 
    # The exit code will be matched with STATUS_CONTROL_C_EXIT or
    # TASK_MANAGER_EXIT and will restart the server if false.
    exitcode = 0x100000000;
    skipexit = False;
    while (skipexit or (exitcode != TASK_MANAGER_EXIT and exitcode != STATUS_CONTROL_C_EXIT)):
        if (skipexit):
            print("srcds manager: launching server after update...");
        else:
            print("srcds manager: launching server...");
        with (subprocess.Popen(argv, cwd = os.path.dirname(os.path.realpath(argv[0])))) as process:
            # Create a new thread to constantly check for updates 
            # and wait for the process to finish. If an update occurs,
            # kill the srcds instance and wait for the thread to finish.
            skipexit = False;
            thread = threading.Thread(target = server_thread, daemon = True, args = [ process, parser, inf ]);
            thread.start();
            while (not (exitcode := process.poll())):
                if (g_bUpdating):
                    process.kill();
                    thread.join();
                    skipexit = True;
        
        # Check if it crashed.
        if (exitcode != 0x100000000 and not skipexit):
            print(f"srcds manager: *WARNING* SERVER CRASHED! (exit code 0x{exitcode:08X})", file = sys.stderr);
    
    print(f"srcds manager: server closed with exit code 0x{exitcode:08X}");
    return 0;

if (__name__ == "__main__"):
    exit(main(len(sys.argv), sys.argv));