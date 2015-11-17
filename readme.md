MSCompose
=========
Given a list of local ManiaScript files in a set order, this project combines all of them into single files by respecting the order or constraints, global variables and functions.
  
Optionally the generated output can be compressed by removing unnecessary comments and whitespaces and output to a XML file which can be included into your Manialink with the `<include>` tag.
 
Usage
-----
Either you create a configuration file by hand and call `python mscompose.py <path_to_your_configfile>` or you start the server to get a UI to help you creating configurations and building projects with `python server.py`.  
  
Further parameters:  
* -p, --port <port-nr> The port to run the server on.
* --open Set this flag to automatically open the GUI in your browser.

Configuration Format
--------------------
```json
{
    "myBuildTarget": {
        "active": True,
        "files": [
        	"script/MyScript1.Script.txt",
        	"script/MyScript2.Script.txt"
        ],
        "outputfile": "Default.Script.txt",
        "compress": False,
        "asXML": False,
        "xmlfile": ""
    }
}
```

Build
-----
Just compile `main.scss` to `main.css` and `index.jade` to `index.html`.