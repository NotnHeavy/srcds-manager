# srcds manager

This is just a simple Python script I wrote for managing a [Source Dedicated Server](https://developer.valvesoftware.com/wiki/Source_Dedicated_Server) on Windows. Much like on Linux (with the `-autoupdate`, `-steam_dir` and `-steamcmd_script` parameters), it will automatically update the server on launch, while running and restart the server if it crashes, potentially from a faulty SourceMod plugin.

## How to use

Create a batch file invoking the `python` runtime with this file (`srcds manager.py`) as the first parameter. Select your desired game with `-game` like you typically would. You will also need to set the directory of your `steamcmd.exe` and the exact path (including the file name) of your SteamCMD script with the parameters `-steam_dir` and `-steamcmd_script` respectively. Otherwise, you can pass the exact same parameters when typically launching your server.

## Dependencies
- [Python 3.8](https://www.python.org/downloads/release/python-380/) or [newer](https://www.python.org/downloads/)
- [requests](https://pypi.org/project/requests/)
