#!/usr/bin/env python
# Runs getIIData.py script

import getIIdata
import os

# For {net, stat, loc} wildcards use '?'
homedir = os.getcwd()
year = '2014'
startday = '001'
network = 'II'
obj = getIIdata.GetArgs(year, startday, network,\
			endday='004', station='?',\
			location='00', channel='LHZ',\
			debug="true", archive="true")
