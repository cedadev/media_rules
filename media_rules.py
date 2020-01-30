



import json
import re
import datetime
import sys
import yaml
import urllib.request

policy_location = "https://raw.githubusercontent.com/cedadev/media_rules/master/policy.yaml"

class StoragePolicy():

    @staticmethod
    def dateparse(s):
        s = s.strip()
        try:
            return datetime.datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            pass 

        days = {"m": 30, "w": 7, "y": 365, "d": 1}
        m = re.match("([\d.]+)\s*(\w)", s)
        if m:
            value, unit = m.groups()
            unit = unit.lower()
            return datetime.timedelta(days=float(value) * days[unit])
        else: 
            raise Exception('Can not interperate "%s" as a YYYY-MM-DD date or a period of form N weeks, N months, N years or N days' % s) 

    def __init__(self, cfg):
        if isinstance(cfg, str):
            cfg = yaml.load(urllib.request.urlopen(cfg), Loader=yaml.SafeLoader)

        if not isinstance(cfg, dict):
            raise ValueError("config needs to be a filename or a dict")

        if "name" in cfg:
            self.name = cfg["name"]
        else:
            self.name = None

        if "regex" in cfg:
            x = cfg["regex"]
            self.regex = re.compile(x)
        else:
            self.regex = re.compile("")

        if "regex_older_than" in cfg:
            self._regex_older_than = self.dateparse(cfg["regex_older_than"])
        else: 
            self._regex_older_than = None

        if "mod_older_than" in cfg:
            self._mod_older_than = self.dateparse(cfg["mod_older_than"])
        else: 
            self._mod_older_than = None

        if "storage" in cfg:
            self.storage = cfg["storage"]
        else:
            raise ValueError("Need a storage list")

        if "larger_than" in cfg:
            self.larger_than = cfg["larger_than"]
        else:
            self.larger_than = None

        self.overridden_by = []
        if "overridden_by" in cfg:    
            for sub_cfg in cfg["overridden_by"]:
                self.overridden_by.append(StoragePolicy(sub_cfg))

    def __repr__(self):
        if self.name is not None:
            s = "%s (%s)" % (self.name, self.regex.pattern)
        else:
            s = "%s" % self.regex.pattern
        if self._mod_older_than is not None:
            s += " mod time older than %s" % self._mod_older_than
        if self._regex_older_than is not None:
            s += " regex time older than %s" % self._regex_older_than
        if self.larger_than is not None:
            s += " >%s bytes" % self.larger_than

        return s

    def tree(self, n=0):
        print("    " * n + "%s" % self)
        for o in self.overridden_by:
            o.tree(n+1)

    def mod_older_than_date(self):
        if isinstance(self._mod_older_than, datetime.timedelta):
            return datetime.datetime.now() - self._mod_older_than
        else: 
            return self._mod_older_than

    def regex_older_than_date(self):
        if isinstance(self._regex_older_than, datetime.timedelta):
            return datetime.datetime.now() - self._regex_older_than
        else: 
            return self._regex_older_than

    def match_storage_policy(self, path, size=None, mod=None):
        match = self.regex.search(path)
        if not match:
            return False

        if self.larger_than is not None:
            if size is None:
                raise ValueError("This policy needs a size to work (%s)" % self)
            if size < self.larger_than:
                return False

        if self._mod_older_than is not None:
            if mod is None:
                raise ValueError("This policy needs a mod time to work (%s)" % self)
            if mod > self.mod_older_than_date():
                return False
 
        if self._regex_older_than is not None:
            gdict = match.groupdict()
            if "year" in gdict and "month" in gdict and "day" in gdict:
                path_date = datetime.datetime(int(gdict["year"]), int(gdict["month"]), int(gdict["day"])) 
                if path_date > self.regex_older_than_date():
                    return False
            else:
                raise ValueError("Need to have year, month and day named groups in the regex to use regex_older_than option.")

        return True

    def find_storage_policy(self, path, size=None, mod=None):
        for o in self.overridden_by:
            if o.match_storage_policy(path, size, mod):
                return o.find_storage_policy(path, size, mod)
        if self.match_storage_policy(path, size, mod):
            return self 

s = StoragePolicy(policy_location)
s.tree()

print()
path = sys.argv[1]
if len(sys.argv) > 2: size = int(sys.argv[2])
else: size = None
if len(sys.argv) > 3: mod = datetime.datetime.strptime(sys.argv[3], "%Y-%m-%d")
else: mod = None

print(path, size, mod)
print(s.find_storage_policy(path, size=size, mod=mod))

#print(s.find_storage_policy("/neodc/sentinel1a/data/x.dat"))
#print(s.find_storage_policy("/neodc/sentinel1a/data//t/y/u/2014/01/03/x.dat", size=20))
#print(s.find_storage_policy("/badc/cmip6/data"))
#print(s.find_storage_policy("/neodc/modis/data/x/y/z"))

