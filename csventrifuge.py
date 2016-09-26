#!/usr/bin/env python

# TODO use a generator instead of loading everything in ram
# TODO count how many times a rule is used, and show unused rules

import csv
import argparse
import os
import re
import importlib

def load_module(wanted_module, origin):
    pysearchre = re.compile('.py$', re.IGNORECASE)
    modulefiles = filter(pysearchre.search,
                         os.listdir(os.path.join(os.path.dirname(__file__),
                                    origin)))
    # form_module = lambda fp: '.' + os.path.splitext(fp)[0]
    modules = map(form_module, modulefiles)
    # import parent module / namespace
    importlib.import_module(origin)
    # modules = {}
    for module in modules:
        if module == '.'+wanted_module:
            return importlib.import_module(module, package="sources")
            break
    # If we reach this point, we haven't found anything
    else:
        raise ImportError('module not found "{}" ({})'.format(wanted_module, origin))


def form_module(fp): return '.' + os.path.splitext(fp)[0]


def is_valid_source(parser, arg):
    if not os.path.exists('sources/'+arg+'.py'):
        parser.error("The input source definition sources/{}.py does not exist".format(arg))
    else:
        return arg


parser = argparse.ArgumentParser(description='Rewrite [source] csv, and output to [output1,output2...]')
parser.add_argument('source', metavar='source', type=lambda x: is_valid_source(parser, x),
                    help='Input source definition')
args = parser.parse_args()


source = load_module(args.source, 'sources')

get_data = getattr(source, 'get', None)

if get_data is None:
    raise ImportError('function not found "{}" ({})'.format('get', args.source))

# Load it all up in memory
data, keys = get_data()

# Open the rules
rulebook = {}
for key in keys:
    # Throw the rules in a dict, e.g. rules['localite'] - according to key->filename
    try:
        with open('rules/'+args.source+'/'+key+'.csv', 'r') as rulecsv:
            rulebook[key] = {}
            for row in csv.reader(rulecsv, delimiter='\t'):
                rulebook[key][row[0]] = row[1]
    except IOError:
        # no rules for this column
        pass

enhancebook = {}
for key in keys:
    try:
        enhancements = os.listdir('enhance/'+args.source+'/'+key)
        if enhancements:
            enhancebook[key] = {}
            for filename in os.listdir('enhance/'+args.source+'/'+key):
                with open('enhance/'+args.source+'/'+key+'/'+filename, 'r') as enhancecsv:
                    # Target is file name without .csv at end
                    target = filename[:-4]
                    keys.append(target)
                    enhancebook[key][target] = {}
                    for erow in csv.reader(enhancecsv, delimiter='\t'):
                        try:
                            enhancebook[key][target][erow[0]] = erow[1]
                        except IndexError:
                            print('erow: '+str(erow))
    except OSError:
        # no enhancements for this column
        pass

# For each address, for each column, if there's a corresponding rule, replace
# if rules['localite'][address['localite']: address['localite'] = rules['localite'][address['localite']
# If there's an enhancement, add that column in the same way.
# Is there a more pythonic way to write this? Lambda function? Dict comprehension?

substitutions = 0

for row in data:
    for key in list(row.keys()):
        try:
            row[key] = rulebook[key][row[key]]
            substitutions += 1
        except KeyError:
            pass
        try:
            for enhancement in enhancebook[key].keys():
                row[enhancement] = enhancebook[key][enhancement][row[key]]
        except KeyError:
            pass

# After substitutions and additions done, spit out new csv.

csv_out = open('csventrifuge-out.csv', 'w')
# extrasaction='ignore' ignores extra fields
# http://www.lucainvernizzi.net/blog/2015/08/03/8x-speed-up-for-python-s-csv-dictwriter/
writer = csv.DictWriter(csv_out, fieldnames=keys, extrasaction='ignore')

writer.writeheader()
writer.writerows(data)
print('{} values out of {} replaced, {:.2%}'.format(substitutions, len(data), substitutions/len(data)))
