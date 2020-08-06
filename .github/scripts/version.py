import requests
from requests_html import HTMLSession
from html.parser import HTMLParser
import yaml
import argparse
# from ruamel.yaml import YAML
# from ruamel.yaml.comments import CommentedMap                                                  
# from ruamel.ordereddict import ordereddict

# Lines 11 to 18 preserve the literal scalar's in the yaml document, this logic can apparently be replaced entirely
# using the ruamel.yaml library but I wasn't able to get this working, maybe another time...
yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str

def repr_str(dumper, data):
    if '\n' in data:                                                                                                                   
        return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
    return dumper.org_represent_str(data)

yaml.add_representer(str, repr_str, Dumper=yaml.SafeDumper)

# Loads a yaml file from the specified filepath and returns a dict
def yaml_loader(filepath):
    with open(filepath, "r") as file_descriptor:
        # yaml = YAML(typ='safe')
        yaml.preserve_quotes = True
        data = yaml.load(file_descriptor, Loader=yaml.FullLoader)
    return data

# Dumps data to a yaml file using a provided filepath and 'data' of type dict
def yaml_dumper(filepath, data):
    with open(filepath, "w") as file_descriptor:
        # yaml = YAML(typ='safe')
        yaml.safe_dump(data, file_descriptor, default_flow_style=False, sort_keys=False)

class MyHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        self.tag_attrs = attrs
    def handle_data(self, data):
        self.data = data

# Dolphin downloads page URL
url = "https://dolphin-emu.org/download/?ref=btn"
 
try:
    session = HTMLSession()
    response = session.get(url)
     
except requests.exceptions.RequestException as e:
    print(e)

# Parse arguments to determine which download version should be fetched
parser = argparse.ArgumentParser(description="script to fetch latest versions")
parser.add_argument('download_type', type=str, nargs=1, help='version of dolphin to be checked (stable, beta, development)')
args = parser.parse_args()

# if args.download_type[0] == "stable":
#     versions = response.html.find('.stable-versions > tbody > tr.infos > td.version.always-ltr')
if args.download_type[0] == "beta":
    versions = response.html.find('#download-beta > table.versions-list.dev-versions > tbody > tr.infos > td.version.always-ltr')
elif args.download_type[0] == "development":
    # The development version always matches the code on the master branch so depending on reliability of this script in the future, this logic may be dropped
    # in favour of building straight from master
    versions = response.html.find('#download-dev > table.versions-list.dev-versions > tbody > tr.infos > td.version.always-ltr')
else:
    print("invalid download type selected")
    quit(1)
# Scrape dolphin downloads page for beta releases
# dev_versions = response.html.find('#download-beta > table.versions-list.dev-versions > tbody > tr.infos > td.version.always-ltr')

# Parsing HTML of scraped contents from dolphin downloads page to obtain source commit and the latest version
parser = MyHTMLParser()
# parser.feed(dev_versions[0].html)
parser.feed(versions[0].html)
if args.download_type[0] == "stable":
    latest_version = parser.data.split(' ')[-1]
else:    
    latest_version = parser.data
    latest_commit = parser.tag_attrs[0][1].split('/')[-2]

# Parsing the snapcraft.yaml file to find the current version to compare against version from downloads page
snapcraft_dict = yaml_loader("snap/snapcraft.yaml")
snap_version = snapcraft_dict["version"]

# Comparing versions and editing snapcraft.yaml if versions don't match
if snap_version != latest_version:
    print("versions don't match:: snap:",snap_version, " latest:", latest_version)
    snapcraft_dict["version"] = latest_version
    snapcraft_dict["parts"]["dolphin-emu"]["source-commit"] = latest_commit
    yaml_dumper("snap/snapcraft.yaml", snapcraft_dict)
    # Creating a file 'build' with the contents being 'true', this is used by the github workflow to determine whether to build the snap
    f = open("build", "a")
    f.write("true")
    f.close()
else:
    print("versions match:: snap:",snap_version, " latest:",latest_version)
    f = open("build", "a")
    f.write("false")
    f.close()

