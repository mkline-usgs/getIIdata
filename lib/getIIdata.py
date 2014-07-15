#!/usr/bin/env python

import glob
import urllib
import os
import argparse
import sys
import datetime
import re, string, time
import numpy.ma as ma

#Here is where we will import our modules

from obspy import UTCDateTime
from obspy.core import read
from obspy.core.trace import Trace
from obspy.core.stream import Stream
from obspy.core.utcdatetime import UTCDateTime
from obspy.fdsn import Client

class GetIIData(object):
	# initialize input vars
	def __init__(self, year, startday, network, **kwargs):
		# initialize year/start/net
		# if statement to check for main args set QUERY=True	
		# else sys.exit(1)
		if (year != "") and (startday != "") and (network != ""):	
			self.year = year
			self.startday = startday
			self.network = network
			QUERY = True
		else:
			QUERY = False

		# loop through **kwargs and initialize optargs
		self.endday = ""	# init endday string
		self.station = "" 	# init station string
		self.location = ""	# init location string
		self.channel = ""	# init channel string
		self.debug = False	# init debug
		self.archive = False	# init archive
		endday = self.endday
		for key,val in kwargs.iteritems(): 
			if key == "endday": self.endday = val
			elif key == "station": self.station = val
			elif key == "location": self.location = val
			elif key == "channel": self.channel = val
			elif key == "debug": self.debug = self.toBool(val)
			elif key == "archive": self.archive = self.toBool(val) 

		# print arguments if 'debug' mode
		if self.debug:
			print "Year: " + self.year
			print "Start Day: " + self.startday
			print "End Day: " + self.endday
			print "Network: " + self.network
			print "Station: " + self.station
			print "Location: " + self.location
			print "Channel: " + self.channel

		# handle wildcards
		if self.location == "?":
			self.location = "*"
		if self.channel == "?":
			self.channel = "*"
		if self.station == "?":
			self.station = "*"

		# set start/end to UTCDateTime object
		#--------------------------------------------------------------------
		self.startTime = UTCDateTime(year + startday +"T00:00:00.000")
		#If no end day in parser default to 1 day
		if self.endday == "?":
			self.endTime = self.startTime + 24*60*60
		else:
			self.endTime = UTCDateTime(year + self.endday +"T00:00:00.000")
		print "Here is our start time " + self.startTime.formatIRISWebService()
		print "Here is our end time   " + self.endTime.formatIRISWebService()
		# Will only run if main args are given
		# check QUERY flag if True continue
		if QUERY:
			self.queryData()
		else:
			print '\nNo main args given.'
			print 'Exiting\n'
			sys.exit(1)
	
	def queryData(self):
		# code from IRIS client 
		#Here we pull the data
		client = Client("IRIS")
		DupStations = []
		DupLocations = []
		DupChannels = []
		self.STAWILD = False
		self.LOCWILD = False
		self.CHANWILD = False
		try:
			requestArray = [(self.network,self.station,self.location, \
				self.channel,self.startTime,self.endTime)]
			print
			if self.debug:
				print(requestArray)
				print 
			self.st = client.get_waveforms_bulk(requestArray)
			for self.tr in self.st:
				#Here we remove the M data quality and go with D
				self.tr.stats.mseed['dataquality'] = 'D'
				if self.debug:
					#print "Here is a trace we have"
					#print(tr.stats)
					if self.station == '*':
						self.STAWILD = True
						DupStations.append(self.tr.stats.station)				
		    			elif self.station != '*':
                				self.STAWILD = False

            				if self.location == '*':
						self.LOCWILD = True	
                				DupLocations.append(self.tr.stats.location)
		    			elif self.location != '*':
						self.LOCWILD = False 
			
					if self.channel == '*':
						self.CHANWILD = True	
                				DupChannels.append(self.tr.stats.channel)
		    			elif self.channel != '*':
						self.CHANWILD = False 
		except:
			print 'Trouble getting data'
			sys.exit(0)
		#takes duplicate stations out of list
		self.stations = list(set(DupStations))
		self.locations = list(set(DupLocations))
		self.channels = list(set(DupChannels))
		print self.stations
		print self.locations
		print self.channels
		# Now call code to store streams in mseed files
		self.storeMSEED()
	
	#LAST THING TO DO!!!!
	def storeMSEED(self):
		#code for storing MSEED files
		#Need to check if the directories exist and if not make them
		#Main program
		codepath = '/home/mkline/dev/getIIdata/TEST_ARCHIVE/'
		self.days = int(round((self.st[-1].stats.endtime \
			- self.st[0].stats.starttime)/(24*60*60)))
		self.stFinal = Stream()

		if self.STAWILD:
			for self.station in self.stations:
				print
				print "For station: " + self.station
				trace = self.st.select(station = self.station)
				trace.merge()
				trace.sort()
				trace.count()
				for dayIndex in range(0,self.days):
					print "Day properties: "
					#startTime works better than trace[0].stats.starttime
					trimStart = self.startTime + (dayIndex)*24*60*60
					trimEnd = self.startTime + (dayIndex+1)*24*60*60
					print "Start of day: " + str(trimStart)
					print "End of day:   " + str(trimEnd)
					#Converting date into julian day
					timesplit = re.split('T', str(trimStart))
					s = timesplit[0]
					fmt = '%Y-%m-%d'
					dt = datetime.datetime.strptime(s, fmt)
					tt = dt.timetuple()
					if tt.tm_yday < 10:
						NewStartDay = '00' + str(tt.tm_yday)
					elif tt.tm_yday < 100:
						NewStartDay = '0' + str(tt.tm_yday)
					else:
						NewStartDay = str(tt.tm_yday)
					self.stFinal = trace.copy()
					self.stFinal.trim(starttime = trimStart, endtime = trimEnd)	
					self.stFinal = self.stFinal.split()
					if not self.stFinal:
						print "No trace for given day"
					else:
						#Added the directory structures in here since you won't want to
						#add directory structures that you don't use
						if not os.path.exists(codepath + self.network + '_' + self.station  + '/'):
							os.mkdir(codepath + self.network + '_' + self.station  + '/')
						if not os.path.exists(codepath + self.network + '_' + self.station  + '/' \
							+ self.year + '/'):
							os.mkdir(codepath + self.network + '_' + self.station  + '/' \
							+ self.year + '/')
						stpath = codepath + self.network + '_' + self.station  + '/' + self.year + \
							'/' + self.year + '_' + NewStartDay + '/'
						if not os.path.exists(stpath):
							os.mkdir(stpath)
						# Here we write the data using STEIM 2 and 512 record lengths
						self.stFinal.write(stpath + self.stFinal[0].stats.location + '_' + \
							self.stFinal[0].stats.channel + '.512.seed', format='MSEED', \
							reclen = 512, encoding='STEIM2')
						print self.stFinal

		elif self.LOCWILD:
			for self.location in self.locations:
				print
				print "For station: " + self.station
				trace = self.st.select(location = self.location)
				trace.merge()
				trace.sort()
				trace.count()
				for dayIndex in range(0,self.days):
					print "Day properties: "
					#startTime works better than trace[0].stats.starttime
					trimStart = self.startTime + (dayIndex)*24*60*60
					trimEnd = self.startTime + (dayIndex+1)*24*60*60
					print "Start of day: " + str(trimStart)
					print "End of day:   " + str(trimEnd)
					#Converting date into julian day
					timesplit = re.split('T', str(trimStart))
					s = timesplit[0]
					fmt = '%Y-%m-%d'
					dt = datetime.datetime.strptime(s, fmt)
					tt = dt.timetuple()
					if tt.tm_yday < 10:
						NewStartDay = '00' + str(tt.tm_yday)
					elif tt.tm_yday < 100:
						NewStartDay = '0' + str(tt.tm_yday)
					else:
						NewStartDay = str(tt.tm_yday)
					self.stFinal = trace.copy()
					self.stFinal.trim(starttime = trimStart, endtime = trimEnd)	
					self.stFinal = self.stFinal.split()
					if not self.stFinal:
						print "No trace for given day"
					else:
						#Added the directory structures in here since you won't want to
						#add directory structures that you don't use
						if not os.path.exists(codepath + self.network + '_' + self.station  + '/'):
							os.mkdir(codepath + self.network + '_' + self.station  + '/')
						if not os.path.exists(codepath + self.network + '_' + self.station  + '/' \
							+ self.year + '/'):
							os.mkdir(codepath + self.network + '_' + self.station  + '/' \
							+ self.year + '/')
						stpath = codepath + self.network + '_' + self.station  + '/' + self.year + \
							'/' + self.year + '_' + NewStartDay + '/'
						if not os.path.exists(stpath):
							os.mkdir(stpath)
						# Here we write the data using STEIM 2 and 512 record lengths
						self.stFinal.write(stpath + self.stFinal[0].stats.location + '_' + \
							self.stFinal[0].stats.channel + '.512.seed', format='MSEED', \
							reclen = 512, encoding='STEIM2')
						print self.stFinal
						

	# convert optional boolean strings to boolean vars
	def toBool(self, value):
		"""
		Converts 'string' to boolean. Raises exception for invalid formats
			True values: 1, True, true, "1", "True", "true", "yes", "y", "t"
			False values: 0, False, false, "0", "False", "false", "no", "n", "f" 
		"""
		if str(value).lower() in ("true", "yes", "t", "y", "1"): return True
		if str(value).lower() in ("false", "no", "f", "n", "0"): return False
		raise Exception('Invalid value for boolean conversion: ' + str(value))

# Subclass GetArgs() passes individual 
# args to superclass GetIIData()
class GetArgs(GetIIData):
	def __init__(self, *args, **kwargs):
		if not args:
			print '\nPass in year, startday, network.'
			print 'Exiting...\n'
			sys.exit(1)

		# store positional args
		year = args[0]
		startday = args[1]
		network = args[2]

		# pass *args and **kwargs to super() class
		super(GetArgs, self).__init__(year, startday, network, **kwargs)

def Help():
	# help file that takes the same format as python parser
	usage = """Usage: This code pulls network data from IRIS and sets 
	it up to be put in a directory structure. The data that is pulled is 
	from the II network given the year and start day that the data is from.
	The end day is an optional arguement; if no end day specified, it will 
	be one day after start day given. Station, location, and channel can be
	wildcards or given a specific value. Only one of these can be wildcarded
	at a time. If the station, location, and channel given do not return any 
	data(trace(s)), IRIS did not collect data for that specific start day given.
	Optionally the user can:
		- specify an end day to collect data for multiple days
		- choose a specific station, location, and/or channel 
		- archive the data if it has yet to be stored in the directory structure
	Arguments will be passed to:
		- GetIIData.GetArgs(posargs,optargs)
		- posargs - positional arguments (network, year, startday)
		- optargs - optional arguments (endday, station, location, channel, debug, archive)
	"""

	posargs = """postional arguments:
	(network = 'II')			\tnetwork in which data is pulled from
	(year = 'YYYY')				\tyear of collected data
	(startday = 'DDD')			\tthe left edge of time series (Julian Day)
	"""
	
	optargs = """optional arguments:
	(endday = 'DDD')			\tthe right edge of time series (Julian Day)
	(station = 'SSSSS')			\tspecific station to where to pull data from
						  (if all stations wanted, enter '?')
	(location = 'LL')			\tspecific location to where to pull data from
						  (if all locations wanted, enter '?')
	(channel = 'CCC')			\tspecific channel to where to pull data from
						  (if all channels wanted, enter '?')
	(debug = 'True/False')			\trun in debug mode
	(archive = 'True/False')		\tarchive the data in /TEST_ARCHIVE
	"""

	print usage
	print posargs
	print optargs


