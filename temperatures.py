#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   
#   for use with Python 3

#	therm19.py :  February 10th 2018
#   march 14th 2018 changed so logs log file without changing file name
#   log file formmat changed so all gaps are underscores (Lines 334 to 336)


#	Copyright 2016  <djgtorrens@gmail.com>
#  
#	This program is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; either version 2 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#  
#	You should have received a copy of the GNU General Public License
#	along with this program; if not, write to the Free Software
#	Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#	MA 02110-1301, USA.
#
#list
#	read set up from a file
#	create that file from the values in the directory
#	log continuosly until  midnight  or any time based on argument passed from commandline
#	get date and time format output suitable for input to php or excel or anything else
#

# socket is for smartplug control
import socket

# all other imports for rest of program
import time
import subprocess
import datetime
import csv
# For Python 3
import configparser
# For Python 2.x would be
#import ConfigParser as configparser
#but this prog no good on Python 2
from ftplib import FTP
from os import listdir
from os import path
from os import fsync
import sys, getopt
import webbrowser
from shutil import copyfile
#Use with
#copyfile(src, dst)

#	data class "config"  is used to hold configuration information
#	the values set in initializing are the default values
#	If no configuration file is found these values are writen to a file "config.cfg"
# put in same directory as the python file.
# the line 
# "  config.prog_path = path.dirname(path.realpath(__file__)) + "/"  " 
# using "path" from "os" module.
# is used to get where to look for and put this file.

class class_config:
	def __init__(self):
		self.scan_delay = 1		# delay in seconds between each scan (not incl sensor responce times)
		self.max_scans = 3			# number of scans to do, set to zero to scan for ever (until type "ctrl C")
		self.log_directory = "/log/"		# where to send log files
		self.ftp_credentials_filename = 'ftp_credentials.csv'	# 
		self.ftp_credentials_log_filename = 'ftp_credentials_log.csv'
		self.ftp_credentials_status_filename = 'ftp_credentials_status.csv'
		self.ftp_credentials_log_html_filename = 'ftp_credentials_log_html.csv'
		self.mount_point = "/rtr/"		# the location to mount the share (must exist) e.g. /home/pi/rtr
		self.test_file = "test.txt"			# a file that should be present at the share if its already mounted e.g.  test.txt
		self.mount_arg1 = "sudo"		# first part of mount command (usually sudo)
		self.mount_arg2 = "/etc/mount_log.sh"		# second part of mount command (usualy name of script to run)
		self.delay_limit = 2		# Number of Seconds delay between temperature scans
		self.delay_increment = 2		# Number of scans to do, Zero for only stopped by Ctrl C on Keyboard
		self.ftplog = 2		# Number of Value Changes before Log File is Saved to remote website
		self.heaterIPa = '192.168.111.100'		# IP for First Heater
		self.heaterIPb = '192.168.111.108'		# IP for Second Heater
		self.sensor4readings = '28-0315a80584ff'  #The code for the sensor to be used to measure room temperature
		self.change4log = 0.6 # change in temperature required before logging and displaying etc
		self.control_hysteresis = 0.15
		# These parameters are not saved to the config.cfg file
		# First three use the program pathname
		self.prog_path = ""
		self.config_filename = ""
		self.sensor_info_filename = ""
		self.logging_filename_save_as = ""
		self.logging_filename = ""
		self.html_filename = ""
		self.status_filename = ""
		self.log_html_filename = ""
		self.local_www_html_filename = ""
		self.local_www_log_html_filename = "" 
		self.local_www_status_htlm_filename = "" 
		self.local_www_log_csv = ""
		self.logging_on = False
		self.sensor_present = False
		self.logging_outfile = ""
		self.scan_count = 0
		self.ftplog_count = 0
		self.ref_sensor_index = 0
		self.heater1_on = 0
		self.heater2_on = 0
		self.one_first = 1
		self.last_target = 0

                                #  SENSORS
class class_sensors:
	def __init__(self):
		self.number = []		# number designation of sensor to use for display
		self.code = []			# the code that the sensor is internally programmed with
		self.connected = []		# true/false flag indicating if his sensor is connected obtained by scanning for its file
		self.reading = []		# the last temperature reading read from the sensor in degrees Centigrade, 
								# wil be a negative value < -100 if there is an error in reading
		self.last_logged = []	# the value last logged for that sensor
		self.code_seen = []		# a trie/false flag indicating that this senso code has been seen during this run
		self.code_seen_but_disconnected = []	# Flag for when we have seen a sensor then its disconnected
		self.location = []		# text read in from the sensor data file for the sensors location
		self.stype = []			# text read in from the sensor data file for the sensors type
		self.comment = []		# text read in from the sensor data file for a comment
		self.delay = []			# if the sesor is not responding, maybe has become disconnected
		self.error_number = []	# then its file will still be present for a while and this number is
		self.last_logged_error_number = [] # Last logged error
		self.status_text = []	# used to count down before retrying, initially set to the observed delay
								# then 0.5 subtracted each scan until value less than 0.5.
								# delay is usually around 2 secosnds so it will be about 3 scans before another attempt is made.

					
class class_schedule:
	def __init__(self):
		self.index = []		# Index of the array holding the Temperature Schedule
		self.year = []		# Year
		self.month = []		# Month
		self.day = []		# Day
		self.hour = []		# Hour
		self.minute = []		# Minute
		self.target_temp = []	# Target Temperature

class class_smartplug():
	def __init__(self,number_of_plugs):
							# NOTE Set for 2 plugs,  
							# must introduce way to set number if need more 
		self.state  = [1.234]*number_of_plugs		# state on is "1" off "0"
		self.ip = ["text"]*number_of_plugs 			# ip address
		self.current = [1.234]*number_of_plugs 		# current
		self.voltage = [1.234]*number_of_plugs  	# voltage
		self.power = [1.234]*number_of_plugs 		# power now
		self.total = [1.234]*number_of_plugs 		# total power (today ?)
		self.error = [1.234]*number_of_plugs 		# error code
		self.sent = ["command"]*number_of_plugs		# last command sent
		self.received = ["reply"]*number_of_plugs	# last reply received

class textbffr(object):
	# Rotating Buffer Class
	# Initiate with just the size required Parameter
	# Get data with just a position in buffer Parameter
	def __init__(self, size_max):
		#initialization
		self.size_max = size_max
		self._data = [""]*(size_max)
		self.posn = self.size_max-1

	def replace(self, value):
		#replace current element
		self._data[self.posn] = value	

	def append(self, value):
		#append an element
		if self.posn == self.size_max-1:
			self.posn = 0
			self._data[self.posn] = value	
		else:
			self.posn += 1
			self._data[self.posn] = value

	def __getitem__(self, key):
		#return stored element
		if (key + self.posn+1) > self.size_max-1:
			return(self._data[key - (self.size_max-self.posn-1)])
		else:
			return(self._data[key + self.posn+1])

# **********************************
# Start of small service functions *
# **********************************

def in_GUI_mode():
	mode = 1
	try:
		if sys.stdin.isatty():
			mode = 0
	except AttributeError:  # stdin is NoneType if not in terminal mode
		pass
	if mode == 0:
		#in terminal mode
		return(False)
	else:
		#in gui mode ...
		return(True)

def list_files(path,exclude):
	# List all files in path "path" bu exclude items matching "exclude"
	# Result is returned as a list
	emptylist= []
	try:
		files = listdir(path)
		#for ind in range(0,len(files)):
		#	if (files[ind] == exclude) or (files[ind][:2] == "00"):
		#		remove(files[ind])
		while exclude in files:
			files.remove(exclude)
		return(files)
	except:
		return(emptylist)	

def pt(where, message):
	global debug
	# routine for use debugging time taken each stage of program
	if debug:
		print("debug(pt) in: " , where , " : ", message, " at : " , str(datetime.datetime.now()), "\n")
	return

def pr(where,message,var_val):
	global debug
	# routine for debugging that prints message then a variables value
	if debug:
		print("debug(pr) in : ", where , " : ", message, str(var_val))
	return

def pr_status(appnd,ref,message):
	global status_bffr
	global last_ref
	# print to screen and to status log and update html file
	print(str(config.scan_count), " : ", message)
	if appnd:
		status_bffr.append(str(config.scan_count) + " : " + make_time_text(datetime.datetime.now()) + " : " + message)
	else :
		if ref == last_ref:
			status_bffr.replace(str(config.scan_count) + " : " + make_time_text(datetime.datetime.now()) + " : " + message)
		else:
			status_bffr.append(str(config.scan_count) + " : " + make_time_text(datetime.datetime.now()) + " : " + message)
	write_html(config.status_filename,status_bffr)
	try:
		copyfile(config.status_filename, config.local_www_status_htlm_filename)
	except:
		pr_log (True,"Fail with send html file to " + config.local_www_status_htlm_filename)
	print ( "FTP for Status file File names  : " +  config.ftp_credentials_status_filename + " : " +  config.status_filename + " : " + "use_cred")
	
	# @@@
	#ftp_result = send_by_ftp(config.ftp_credentials_status_filename, config.status_filename,"use_cred")	
	ftp_result = "257"
	
	# uncomment next lines for more info on FTP reults
	#for pres_ind in range(0, len(ftp_result)):
	#	print (ftp_result[pres_ind])
	last_ref = ref
	return

def pr_log(appnd,message):
	global log_bffr
	# print to screen and to status log and update html file
	print(str(config.scan_count) + " : ",message)
	if appnd :
		log_bffr.append(str(config.scan_count) + " : " + message)
	else:
		log_bffr.replace(str(config.scan_count) + " : " + message)
	write_html(config.log_html_filename,log_bffr)
	try:
		copyfile(config.log_html_filename, config.local_www_log_html_filename)
	except:
		pr_status(True,0, "Fail with send html file to " + config.local_www_log_html_filename)
	print ( "FTP for log html file File names   : " +  config.ftp_credentials_log_html_filename + " : " +  config.log_html_filename + " : " + "use_cred")
	
	# @@@
	#ftp_result = send_by_ftp(config.ftp_credentials_log_html_filename, config.log_html_filename,"use_cred")	
	ftp_result = "282"
	
	# uncomment next lines for more info on FTP reults
	#for pres_ind in range(0,len(ftp_result)):
	#	print (ftp_result[pres_ind]	)
	#return


def fileexists(filename):
	#This checks for file but does not detect disconnected sensor
	try:
			with open(filename): pass
	except IOError:
			return False 
	return True

def mount_log_drive(mount_point,test_file,mount_arg1,mount_arg2):
	
	# NOT IN USE AT THE MOMENT IN thermoxx.py
	
	#  mount_point	: 	the location to mount the share (must exist) e.g. /rtr
	#  test_file 	:	a file that should be present at the share if its already mounted e.g.  test.txt
	#  mount_arg1	:	first part of mount command (usually sudo)
	#  mount_arg2	:	second part of mount command (usualy name of script to run such as 'sudo /etc/mount_log.sh')
	#		typical script command "sudo mount -t cifs //192.168.1.1./log /home/pi/rtr -o credentials=/etc/mountcred,sec=ntlm
	#		credentials_file:  a file containing the username and password (located in \etc) for the share e.g.  mountcred
	#				typical credentials file:
	#					username=fredblogs
	#					password=reallysecurepassword

	#check to see if the network drive for logging is mounted, if not then mount it
	here = "mount_log_drive"
	if (fileexists(mount_point + test_file)):
			pr_status(True,0, "Log Drive already mounted because " + mount_point + test_file + " exists")
			return ("Log Drive already mounted\n")
	else:
			pr_status(True,0, "Will use mount command: " + mount_arg1 +  " " + mount_arg2 + "\n")
			subprocess.call([mount_arg1,mount_arg2]) # e.g. applies 'sudo /etc/mount_log.sh' as two parts of the command
			return("Log Drive now mounted\n")

def show_html(html_filename):
	# open a file in the default program
	here = "show_html"
	pr(here, "Show file at this url : ", " file://" + html_filename)
	url = "file://" + html_filename
	webbrowser.open(url,new=2) # new=2 signals new tab

def print_bffr(bffr): 
	#print to screen contaents of a buffer
	for ind in range(bffr.size_max-1,-1,-1):
		stored = bffr[ind]
		if stored != "":
			print(stored)
	print ( '\n' )
	
def write_html(html_filename,bffr):
	#send contemts of buffer to website
	with open(html_filename,'w') as htmlfile:
		htmlfile.write("<p>" + html_filename + " : " + make_time_text(datetime.datetime.now())  + "</p>")
		for ind in range(bffr.size_max-1, -1,-1):
			htmlfile.write("<p>" + bffr[ind] + "</p>")
	
def make_time_text(time_value):
	#make a time stamp in format mm:dd hr:mn:sc
	return(str(time_value.month).zfill(2) + "_" + str(time_value.day).zfill(2) + "__"
	  + str(time_value.hour).zfill(2) + "_" + str(time_value.minute).zfill(2) +"_"
	  + str(time_value.second).zfill(2))




# **********************************
#  End  of small service functions *
# **********************************

# ************************************
#  Start smartplug service functions *
# ************************************

# Check if IP is valid
def validIP(ip):
	try:
		socket.inet_pton(socket.AF_INET, ip)
	except socket.error:
		parser.error("Invalid IP Address.")
	return ip 

# Predefined Smart Plug Commands
# For a full list of commands, consult tplink_commands.txt
commands = {'info'     : '{"system":{"get_sysinfo":{}}}',
			'on'       : '{"system":{"set_relay_state":{"state":1}}}',
			'off'      : '{"system":{"set_relay_state":{"state":0}}}',
			'read'     : '{"emeter":{"get_realtime":{}}}' 
}

# Encryption and Decryption of TP-Link Smart Home Protocol
# XOR Autokey Cipher with starting key = 171
#revied code refer https://github.com/softScheck/tplink-smartplug/issues/20 
def encrypt(string):
    key = 171
    result = b"\0\0\0"+ chr(len(string)).encode('latin-1')
    for i in string.encode('latin-1'):
        a = key ^ i
        key = a
        result += chr(a).encode('latin-1')
    return result

def decrypt(string):
    key = 171 
    result = ""
    for i in string: 
        a = key ^ i
        key = i 
        result += chr(a)
    return result
	
def get_json(string,value):
	try:
		pos = string.find(":",string.find(value))
		if pos == -1 :
			return -1
		else:	
			end1 = string.find(",",pos)
			end2 = string.find("}",pos)	
		try:
			return float(string[pos+1:end1])
		except:
			try:
				return float(string[pos+1:end2])
			except:
				return -1
	except: return -99 

def  send_command(cmded,ip,port) :
	try:
		sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock_tcp.connect((ip, port))
		sock_tcp.send(encrypt(cmded))
		data = sock_tcp.recv(2048)
		sock_tcp.close()
		return decrypt(data[4:])
	except:
		return ("error")
		
def get_smartplug_status():
	global smartplug_info

	#temporary until imlement file to hold smartplug info separatly
	smartplug_info.ip[0] = config.heaterIPa
	smartplug_info.ip[1] = config.heaterIPb
	#smartplug_info.ip[2] = "192.168.222.63"
	#smartplug_info.ip[3] = "192.168.222.64"

	for index in range(0,len(smartplug_info.ip),1):
		cmd = commands["read"]
		result = send_command(cmd,smartplug_info.ip[index],9999)
		if result != "error" :
			st_cmd = commands["info"]
			smartplug_info.state[index] = get_json(send_command(st_cmd,smartplug_info.ip[index],9999),"relay_state")
			smartplug_info.current[index] = get_json(result,"current")
			smartplug_info.voltage[index] = get_json(result,"voltage")
			smartplug_info.power[index] = get_json(result,"power")
			smartplug_info.total[index] = get_json(result,"total")
			smartplug_info.error[index] = get_json(result,"err_code")
			smartplug_info.sent[index] = cmd
			smartplug_info.received[index] = result
		else:
			pr_status(True,0, "Error connecting to Smartplug on : " + smartplug_info.ip[index])

def turn_on_smartplug(index):
	global config
	cmd = commands["on"]
	send_command(cmd,smartplug_info.ip[index],9999)			

def turn_off_smartplug(index):
	global config
	cmd = commands["off"]
	send_command(cmd,smartplug_info.ip[index],9999)

		

# ************************************
# End of smartplug service functions *
# ************************************

def init(margs):
	global config
	global sensors
	global temps_dir
	global exclude_filename
	global debug
	global error
	global run_mode
	global smartplug_info
	global status_bffr
	global log_bffr
	
	here = "init" 
	debug = False
	config = class_config() # set all to defaults
	config.last_target = 0
	starttime = datetime.datetime.now()
	timestamp = make_time_text(starttime)

	#timestamp = str(starttime.month).zfill(2) + "_" + str(starttime.day).zfill(2) + "_" +  str(starttime.hour).zfill(2)  + "_" +  str(starttime.minute).zfill(2)
	
	#*****************************************************
	# (1) determin the programs location and mode
	#		()	
	config.prog_path = path.dirname(path.realpath(__file__))
	print ("config.prog_path : " + config.prog_path )
	config.config_filename = config.prog_path + "/" + "config.cfg"
	print ("config.config_filename : " +  config.config_filename) # OK
	config.sensor_info_filename = config.prog_path + "/" + "sensor_data.csv"
	print ("config.sensor_info_filename: " + config.sensor_info_filename )
	config.logging_filename_save_as = timestamp + "lg.csv"
	print ("config.logging_filename_save_as: " + config.logging_filename_save_as )
	config.logging_filename =  config.prog_path + config.log_directory + config.logging_filename_save_as
	print ("config.logging_filename: " + config.logging_filename )
	config.html_filename = config.prog_path + "/" + "index.html"
	print ("config.html_filename: " + config.html_filename)
	config.status_filename = config.prog_path + "/" +"status.html"
	print ("config.status_filename: " + config.status_filename )
	config.log_html_filename = config.prog_path + "/" + "log.html"
	print ("config.log_html_filename : " +  config.log_html_filename)
	config.local_www = "/var/www/html"
	print ("config.local_www: " + config.local_www )
	
	config.local_www_html_filename = config.local_www + "/" +"index.html"
	print ("config.local_www_html_filename: " + config.local_www_html_filename )
	
	config.local_www_log_html_filename = config.local_www + "/" + "log.html"
	print ("config.local_www_log_html_filename : " +  config.local_www_log_html_filename)
	
	config.local_www_status_htlm_filename = config.local_www + "/" + "status.html"
	print ("config.local_www_status_htlm_filename: " +  config.local_www_status_htlm_filename )
	
	config.local_www_log_csv = config.local_www + "/" + config.logging_filename_save_as
	print ("config.local_www_log_csv: " +  config.local_www_log_csv)

	#*****************************************************
	# (2) Load in Configuration from config.cfg
	#		(If no file then save defaults to config.cfg file)

	pr(here, "Will look for this config file : ",  config.config_filename)
	#set up configuration
	if fileexists(config.config_filename):
		pr(here,  "Reading config file : ", config.config_filename)
		config_read(config.config_filename) # overwrites from file
	else:
		pr(here,  "File not found so writing config file : ", config.config_filename)
		config_write(config.config_filename,config) # writes defaults to file
	pr(here, "configuration Info : ",config.__dict__)
	
	#*****************************************************
	# (3) Load in Configuration from config.cfg
	#		(If no file then save defaults to config,cfg file)
	try:
		opts, args = getopt.getopt(margs,"hdpsc")
	except getopt.GetoptError:
		pr_status(True,0, "NOT correct ption Usage try -h")
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-d':
			debug = True
			pr(here, "Debug on : ", opt)
		if opt == '-h':
			pr(here, "Set option show help file : ", opt)
			if in_GUI_mode():
				show_html(config.prog_path + "/"+"help.html")
			else:
				subprocess.call(['nano', config.prog_path + "/"+"help.html"])
			#show_html(config.prog_path + "/"+"help.html")
			sys.exit()
		if opt == '-p':
			pr ("\"-p\" option on: (does nothing) : ", opt)
		if opt == '-s':
			if not fileexists(config.sensor_info_filename):
				pr_status(True,0,"Creating config.cfg file with default values")
				# sensors = class_sensors()  not needed I think
				new_codes_count = check_what_is_connected()
				# then if there are any new we have not seen before write to the sensor file
				if new_codes_count >0 :
					pr_status(True,0,"Sensor Data filecreated and can now be edited. It has "+ new_codes_count + " entries" )
					write_sensor_data(new_codes_count,True)
				else:
					pr_status(True,0,"No sensors connected Pleae connect at least one")
					sys.exit()
			pr(here, "Set option show sensor data file file : ", opt)
			if in_GUI_mode():
				show_html(config.sensor_info_filename)
			else:
				subprocess.call(['nano', config.sensor_info_filename])
			pr_status(True,0,"Sensor Data file can now be edited.")
			sys.exit()
		if opt == '-c':
			if not fileexists(config.config_filename):
				pr_status(True,0,"Creating config.cfg file with default values")
				config_write(config.config_filename,config)
				#create sensor data file
			pr_status(True,0,"Config file can now be edited")
			pr(here, "Set option show config file : ", opt)
			if in_GUI_mode():
				show_html(config.config_filename)
			else:
				subprocess.call(['nano', config.config_filename])
			sys.exit()
  
	#*****************************************************
	# (4) mount remote drive using parameters from config.cfg
	#		(mount_point,test_file,mount_arg1,mount_arg2)
	
	# NOT USED AT THE MOMENT IN thermoxx.py
	#print(mount_log_drive(config.mount_point,config.test_file,config.mount_arg1,config.mount_arg2),"\n")

	#*****************************************************
	# (5) set up log file using parameters from config.cfg
	#		(file based is based on current time)

	if len(config.log_directory) > 0:
		config.logging_outfile = open(config.logging_filename,'w')
		config.logging_on = True
	else:
		config.logging_on = False
		config.logging_filename = None
		config.logging_outfile = ""

	#*****************************************************
	# (6) Make sure the Gpio and thermometer modules are loaded
	#		()
	
	#Commented out for test
	#subprocess.call(['sudo','modprobe', 'w1-gpio'])
	#subprocess.call(['sudo','modprobe', 'w1-therm'])
	
	#*****************************************************
	# (7) set up empty lists to hold sensor data
	#		(see "class_sensors" for iformation)
	sensors = class_sensors()	


	
	#*****************************************************
	# (8) set up empty lists to hold smartplug info
	#		(see "class_smartplug" for information)
	#  NOTE: Class is set from here for 2 (two) plugs
	smartplug_info = class_smartplug(2)
	
	#*****************************************************
	# (9) set up error codes
	#		()

	error=["OK","1File only","2New no Data","3Timeout","4CRC er",
		"5Read Err","6Retry Err","7Error","8No Data","9No Dev","10Disconn"]
		
	#*****************************************************
	# (10) set up buffers
	#
	log_bffr = textbffr(100)
	status_bffr = textbffr(200)	

def write_sensor_data(new_data_count, new_file):
	# add a new record to the sensor file
	global sensors
	global config
	global smartplug_info
	
	here = "write_sensor_data"
	pr(here, "write_sensor_data will write : ", new_data_count)
	fields = ['number','code','location','stype','comment']
	# 'at' mode adds to end of the file and opens file as text
	if new_file:
		mode = 'wt'
	else:
		mode = 'at'
	try:
		with open(config.sensor_info_filename, mode) as sensorcsv_file:
			writer = csv.DictWriter(sensorcsv_file, fieldnames = fields)
			if new_file: # this is a blank file
				writer.writeheader() # new file needs headings.
			for line_count in  range(len(sensors.code)-new_data_count,len(sensors.code),1):
				# We need to write to the new line with "number,code,location,stype,comment"
				writer.writerow({
				'number': sensors.number[line_count],
				'code': sensors.code[line_count],
				'location': sensors.location[line_count],
				'stype': sensors.stype[line_count],
				'comment': sensors.comment[line_count]
				})
	except:
		pr_status(True,0,"Error accessing the existing sensor info file")
		pr_status(True,0,"Close the file if you are editing it!")
		sys.exit()
	return 0

def config_read(c_filename):
	here = "config_read"
	config_read = configparser.RawConfigParser()
	config_read.read(c_filename)
	config.scan_delay = float(config_read.getint('SetUp', 'scan_delay')) 
	config.max_scans = int(config_read.getint('SetUp', 'max_scans'))
	config.log_directory = config_read.get('SetUp', 'log_directory')
	config.ftp_credentials_filename = config_read.get('SetUp', 'ftp_credentials_filename') 
	config.ftp_credentials_log_filename = config_read.get('SetUp', 'ftp_credentials_log_filename') 
	config.ftp_credentials_status_filename = config_read.get('SetUp', 'ftp_credentials_status_filename') 
	config.ftp_credentials_log_html_filename= config_read.get('SetUp', 'ftp_credentials_log_html_filename') 
	config.mount_point = config_read.get('SetUp', 'mount_point')
	config.test_file = config_read.get('SetUp', 'test_file')
	config.mount_arg1 = config_read.get('SetUp', 'mount_arg1')
	config.mount_arg2 = config_read.get('SetUp', 'mount_arg2')
	config.delay_limit = float(config_read.get('SetUp', 'delay_limit'))
	config.delay_increment = float(config_read.get('SetUp', 'delay_increment'))
	config.ftplog = float(config_read.get('SetUp', 'ftplog'))
	config.heaterIPa = config_read.get('SetUp', 'heaterIPa')
	config.heaterIPb = config_read.get('SetUp', 'heaterIPb')
	config.sensor4readings = config_read.get('SetUp', 'sensor4readings')
	config.change4log = config_read.get('SetUp', 'change4log')
	config.control_hysteresis = config_read.get('SetUp', 'control_hysteresis')
	return

def config_write(c_filename,default_config):
	here = "config_write"
	config_write = configparser.RawConfigParser()
	config_write.add_section('SetUp')
	config_write.set('SetUp', 'scan_delay',default_config.scan_delay)
	config_write.set('SetUp', 'max_scans',default_config.max_scans)
	config_write.set('SetUp', 'log_directory',default_config.log_directory)
	config_write.set('SetUp', 'ftp_credentials_filename',default_config.ftp_credentials_filename)
	config_write.set('SetUp', 'ftp_credentials_log_filename',default_config.ftp_credentials_log_filename)
	config_write.set('SetUp', 'ftp_credentials_status_filename',default_config.ftp_credentials_status_filename)
	config_write.set('SetUp', 'ftp_credentials_log_html_filename',default_config.ftp_credentials_log_html_filename)
	config_write.set('SetUp', 'mount_point',default_config.mount_point)
	config_write.set('SetUp', 'test_file',default_config.test_file)
	config_write.set('SetUp', 'mount_arg1',default_config.mount_arg1)
	config_write.set('SetUp', 'mount_arg2',default_config.mount_arg2)
	config_write.set('SetUp', 'scan_delay',default_config.scan_delay)
	config_write.set('SetUp', 'delay_limit',default_config.delay_limit)
	config_write.set('SetUp', 'delay_increment',default_config.delay_increment)
	config_write.set('SetUp', 'ftplog',default_config.ftplog)
	config_write.set('SetUp', 'heaterIPa',default_config.heaterIPa)
	config_write.set('SetUp', 'pheaterIPb',default_config.heaterIPb)
	config_write.set('SetUp', 'sensor4readings',default_config.sensor4readings)
	config_write.set('SetUp', 'change4log',default_config.change4log)
	config_write.set('SetUp', 'control_hysteresis',default_config.control_hysteresis)
# Writing our configuration file to 'c_filename'
	pr(here, "ready to writenew : " , c_filename)
	with open(c_filename, 'w+') as configfile:
		config_write.write(configfile)
	return 0

def read_in_sensor_data(s_filename):
	#	Set sensor data lists with initial values
	#	read in from file if it exists if not then set up
	#	just defaults for one sensor
	#	later any sensors that are connected will be added
	global sensors
	global smartplug_info
	global config
	here = "read_in_sensor_data"
	pr(here, "dictionary of sensors : ", sensors.__dict__ )
	with open(s_filename, 'r') as csvfile:
		d_file = csv.DictReader(csvfile)
		ind = 0
		for row in d_file:
			sensors.number.append(row['number'])
			sensors.code.append(row['code'])
			sensors.connected.append(False)
			sensors.reading.append(-108)
			sensors.last_logged.append(-108)
			sensors.code_seen.append(False)
			sensors.code_seen_but_disconnected.append(False)
			sensors.location.append(row['location'])
			sensors.stype.append(row['stype'])
			sensors.comment.append(row['comment'])
			sensors.delay.append(0)
			sensors.error_number.append(2)
			sensors.last_logged_error_number.append(2)
			sensors.status_text.append("?")
		ind += 1
	return(True)

def read_in_schedule_data(sch_filename):
	#	Read in Schedule data from schedule.csv
	global sensors
	global smartplug_info
	global config
	global schedule
	here = "read_in_schedule_data"
	pr(here, "Schedulke Data read in : ", schedule.__dict__ )
	with open(sch_filename, 'r') as csvfile:
		d_file = csv.DictReader(csvfile)
		ind = 0
		for row in d_file:
			if int(row['index']) < 10 :
				print ( row['index'],row['year'],row['month'],row['day'],row['hour'],row['minute'],row['target_temp'])
			schedule.index.append(row['index'])
			schedule.year.append(row['year'])
			schedule.month.append(row['month'])
			schedule.day.append(row['day'])
			schedule.hour.append(row['hour'])
			schedule.minute.append(row['minute'])
			schedule.target_temp.append(row['target_temp'])
		ind += 1
	return(True)
	
def send_by_ftp(ftp_cred,send_filename, save_as_filename):
	here = "send_by_ftp"
	result = ["FTP attempt for :" + send_filename]
	try:
		with open(ftp_cred, 'r') as csvfile:
			cred_file = csv.DictReader(csvfile)
			ind = 0
			for row in cred_file:
				if ind == 0:
					ftp_user = row['user']
					pr(here ,"ftpuser : ",ftp_user)
					ftp_password = row['password']
					pr(here,"ftp password : ", ftp_password)
					file_2_send = str(send_filename)
					if save_as_filename == "use_cred":
						#use filename from credentials file
						file_as = str(row['file_as'])
					else:
						# use file from function parameter
						file_as = save_as_filename
					ftp_directory = str(row['directory'])
					pr(here, "ftp directory : ",ftp_directory)
					ftp_site =  str(row['site'])
					pr(here, "ftp site : ", ftp_site)
				else:
					result.append("Error more than one line in FTP Credentials file")
					return(result)
				ind += 1
		ftp = FTP()
		pr(here,"Will try to connect to : ", ftp_site)
		ftp.connect(ftp_site, 21)
		pr(here, "logging in here is ftp welcome message : ",ftp.getwelcome())
		ftp.login(user=ftp_user,passwd=ftp_password)
		pr(here, "logged in to : ",ftp_site)
		ftp.cwd(ftp_directory)
		pr(here, "directory changed to : ", ftp_directory)  
	
		sendfile  = open(send_filename,'rb')
		# remove # on next line for debug
		result.append("Will try to send : " + send_filename + " : as : "
		             + file_as + " to : " +  ftp_site + "/" + ftp_directory)
		ftp.storbinary('STOR ' + file_as,sendfile)
		sendfile.close()
		
		ftp.quit()
		pr(here, "ftp quitedfrom : ", ftp_site)
		return(result)
	except:
		result.append("Error Trying To Send " + send_filename + " file by FTP")
		return(result)
	

def send_temperature_data_using_ftp(ftp_credentials_file):
	global config # set n init() used to hold FTP credentials
	global sensors # sensor data
	global smartplug_info
	global target_temp

	here = "send_temperature_data_using_ftp"
	ftp_text_top = ["\t<!--"]
	ftp_text_top.append("\Temperature Logging and Control")
	ftp_text_top.append("\t-->")
	ftp_text_top.append("<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Strict//EN\"")
	ftp_text_top.append("\t\"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd\">")
	ftp_text_top.append("<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\" lang=\"en\">")
	ftp_text_top.append("<head>")
	ftp_text_top.append("\t<title>Temperature Logging and Control</title>")
	ftp_text_top.append("\t<meta http-equiv=\"content-type\" content=\"text/html;charset=utf-8\" />")
	ftp_text_top.append("\t<meta name=\"generator\" content=\"Geany 1.27\" />")
	ftp_text_top.append("\t<meta http-equiv=\"refresh\" content=\"15\" />")
	ftp_text_top.append("</head>")
	ftp_text_top.append("Scan Count: " + str(config.scan_count) + " System Time: " 
						+ make_time_text(datetime.datetime.now()) + " Log File: "  + str(config.logging_filename_save_as))
	ftp_text_top.append("<body>")
	ftp_text_top.append("<table style=\"background-color: #f4e7e7; width: 350px; height: 150px; border: 1px solid #1b58e4;\" cellpadding=\"5\" align=\"center\"><caption>Temperature Monitoring Degrees C  01</caption>")
	ftp_text_top.append("<tbody>")
	ftp_text_linestart = "<tr align=\"center\" valign=\"middle\"><td>"
	ftp_text_between = "</td><td>"
	ftp_text_line_end = "</td></tr>"
	ftp_text_end = ["</tbody>"]
	ftp_text_end.append("</table>")
	ftp_text_end.append("</body>")
	ftp_text_end.append("</html>")
	with open(config.html_filename,'w') as htmlfile:
		for element in ftp_text_top:
			htmlfile.write(element)
		s_numb = 0
		for element in sensors.number:
			htmlfile.write(ftp_text_linestart + str(element) + ftp_text_between + str(sensors.location[s_numb]) + ftp_text_between + str(sensors.status_text[s_numb]) + ftp_text_line_end)
			s_numb +=1
		htmlfile.write(ftp_text_linestart + "Plug 1 Power and Total" + ftp_text_between + str(smartplug_info.power[0]) + ftp_text_between + str(smartplug_info.total[0]) + ftp_text_line_end)
		htmlfile.write(ftp_text_linestart + "Plug 2 Power and Total"+ ftp_text_between + str(smartplug_info.power[1]) + ftp_text_between + str(smartplug_info.total[1]) + ftp_text_line_end)
		htmlfile.write(ftp_text_linestart + "Scehduled" + ftp_text_between + "Target Temp : " + ftp_text_between + str(target_temp) + ftp_text_line_end)
		for element in ftp_text_end:
			htmlfile.write(element)
	
	print ( "FTP for index html File names : " + " " + ftp_credentials_file + " : " + config.html_filename + " : " + "use_cred")
	
	# @@@
	#ftp_result = send_by_ftp(ftp_credentials_file, config.html_filename,"use_cred")
	ftp_result = "884"
	
	# uncomment following two for print of FTP
	#for pres_ind in range(0,len(ftp_result)):
	#	print (ftp_result[pres_ind])
	
	try:
		# send the same html file to the local web site
		copyfile(config.html_filename, config.local_www_html_filename)
		# remove # on next line for debug
		# pr_status(True,0, "Sent : " + config.html_filename + " to : " + config.local_www_html_filename)
	except:
		pr_status(True,0,"Fail with copy " + config.html_filename + " to : " + config.local_www_html_filename)
	


def check_what_is_connected():
	# check which sensors are connected and update relavant flags
	# build a list of all the new sensors and then add them to the data in use
	global sensors
	global dropped_list
	global smartplug_info
	global config
	here = "check_what_is_connected"
	# Look for what sensors are connected 
	temps_dir = '/sys/bus/w1/devices'
	exclude_filename = "w1_bus_master1"
	connected_codes = list_files(temps_dir,exclude_filename)
	if len(connected_codes) > 0:
		config.sensor_present = True
		pr(here, "Sensor present Set True with count equal to : ", str(len(connected_codes)))
	else:
		pr(here, "Sensor present not Set with count equal to : ", str(len(connected_codes)))
		config.sensor_present = False
	new_codes = []
	count_data = 0
	config.ref_sensor_index = -1
	dropped_list = ""
	for element in sensors.code:
		if element in connected_codes:
			# set flag to indicate has been seen during this run of program
			sensors.code_seen[count_data] = True
			if sensors.code[count_data] == config.sensor4readings:
				config.ref_sensor_index = count_data
			sensors.code_seen_but_disconnected[count_data] = False
			# set flag showing it is connected now or very recently
			# (file persists for a while after sensor removed)
			sensors.connected[count_data] = True 
			sensors.reading[count_data] = -101 # should be over writen by temp data
		else:
			sensors.connected[count_data] = False
			if sensors.code_seen[count_data]:
				sensors.code_seen_but_disconnected[count_data] = True
				dropped_list = dropped_list + " " + sensors.number[count_data]
		count_data  += 1
	count_connected = 0
	new_codes = []
	for element in connected_codes:
		if not element in sensors.code:
			new_codes.append(element)
		count_connected  += 1
	if len(new_codes) > 0:
		pr_log(True, str(len(new_codes))  + " new sensors found")
		pr(here, " New sensors found ",len(new_codes))
		for ind in range(0, len(new_codes)):
			if len(sensors.number) > 0:
				sensors.number.append("n" + str(count_connected-len(new_codes)+ind+1))
			else:
				sensors.number.append("n" + str(1))
			sensors.code.append(new_codes[ind])
			sensors.connected.append(True)
			sensors.reading.append(-102)
			sensors.last_logged.append(-102)
			sensors.code_seen.append(True)
			sensors.code_seen_but_disconnected.append(False)
			sensors.location.append("New Sensor " + str(sensors.number[ind]) + " Location")
			sensors.stype.append("New Sensor " + str(sensors.number[ind]) + " Type")
			sensors.comment.append("New Sensor " + str(sensors.number[ind]) + " Comment")
			sensors.delay.append(0)
			sensors.error_number.append(2)
			sensors.status_text.append("New")
			sensors.last_logged_error_number.append(2)
	else:
		pr(here, "no new codes, still only : ", str(count_connected) + " connected")
	return(len(new_codes))

def get_temperature(no):
	global sensors
	global config
	global smartplug_info

	here = "get_temperature"	
	file_data = {}
	filename = "/sys/bus/w1/devices/"+sensors.code[no]+"/w1_slave"
	#Routine to read the temperature
	#Read the sensor 3 times checking the CRC until we have a good read
	for retries in range(1, 4):
		start_look = datetime.datetime.now()
		pr(here, "sensor : " + str(no + 1) + " retry : " + str(retries) + " delay_count : ", sensors.delay[no])
		try:
			with open(filename, newline='') as csvfile:
				temps_reader = csv.reader(csvfile, delimiter=' ', quotechar='|')
				rownum = 0
				maxcol = 0
				try:
					for row in temps_reader:
						if rownum == 0:
							elapsed = datetime.datetime.now()- start_look
						if (elapsed.total_seconds())>2:
							sensors.delay[no] = elapsed.total_seconds() # remember the delay 
							pr(here, "Sensor Delay : " + str(sensors.number[no]) + " with delay of : " + str(sensors.delay[no]) + " delay count set to : ",sensors.delay[no])
							sensors.reading[no] = -103
							sensors.error_number[no] = 3
							return # delay too big
						colnum =0
						for col in row:
							file_data[rownum,colnum] = col
							if colnum > maxcol:
								maxcol = colnum
							colnum += 1
						rownum += 1
				except:
					sensors.reading[no] = -109
					sensors.error_number = 9
					return
				try:	
					pr(here, "max col found was : ", maxcol)
					pr(here, "file_data[0,11](CRC check) was : ", file_data[0,11])
					pr(here, "temp_str was : ", file_data[1,9])
				except:
					pr_status(True,0, here + "not getting data from file read time was : " +  elapsed.total_seconds())
				try:
					if (maxcol == 11) and (file_data[0,11] == "YES"): # file and CRC reading OK
						temp_str = file_data[1,9] # get temperature data in format "t=NN.NNN"
						temp_int = float(temp_str[2:]) # extract the number
						temp_val = temp_int / 1000 # move decimal point
						sensors.reading[no] = float(temp_val)
						sensors.error_number[no] = 0
						return # convert to float and return
					else:
						sensors.reading[no] = -104
						sensors.error_number[no] = 4
						return # return read error
				except:
					sensors.reading[no] = -105
					sensors.error_number[no] = 5
					return # signals that read file but CRC bad
		except:
			#comes her if file goes between the "check_what_is_connected()" scan and now
			sensors.reading[no] = -110
			sensors.error_number[no] = 10
			return # file gone
	if retries > 3:
		sensors.reading[no] = -106
		sensors.error_number[no] = 6
		return
	sensors.reading[no] = -107
	sensors.error_number[no] = 7
	return # return read error

def log_temperature_data_to_file():
	global config
	global sensors
	global smartplug_info
	here = 	"log_temperature_data_to_file"
	#write the time at the start of the line in logging file
	logtime = datetime.datetime.now()
	config.logging_outfile.write(str(logtime.day).zfill(2) + "/" + str(logtime.month).zfill(2) + 
		"/" + str(logtime.year).zfill(2) + " " + str(logtime.hour).zfill(2) + ":" + 
		str(logtime.minute).zfill(2) + ":" + str(logtime.second).zfill(2))
	if (config.sensor_present == False):
		config.logging_outfile.write(" : no sensors with Trg Temp of : " + str(target_temp) + "\n")
	else:
		config.logging_outfile.write(",TrgTemp: ," + str(target_temp) + ",")
		for z in range(0,len(sensors.code),1):
			#record the data last saved for this sensor
			#send data to the file only if the sensor is connected
			if sensors.code_seen[z]:
				config.logging_outfile.write(" , " + str(sensors.number[z]) + " , " + str(sensors.status_text[z]))
				sensors.last_logged[z] = sensors.reading[z]
				sensors.last_logged_error_number[z] = sensors.error_number[z]
		
		get_smartplug_status()
				
		config.logging_outfile.write("," + str(smartplug_info.state[0]))
		config.logging_outfile.write("," + str(smartplug_info.current[0]))
		config.logging_outfile.write("," + str(smartplug_info.voltage[0]))
		config.logging_outfile.write(" , " + str(smartplug_info.power[0]))
		config.logging_outfile.write("," + str(smartplug_info.total[0]))
		config.logging_outfile.write("," + str(smartplug_info.error[0]))
		config.logging_outfile.write("," + str(smartplug_info.state[1]))
		config.logging_outfile.write("," + str(smartplug_info.current[1]))
		config.logging_outfile.write("," + str(smartplug_info.voltage[1]))
		config.logging_outfile.write("," + str(smartplug_info.power[1]))
		config.logging_outfile.write("," + str(smartplug_info.total[1]))
		config.logging_outfile.write("," + str(smartplug_info.error[1]))
		config.logging_outfile.write("\n")
		config.logging_outfile.flush()

	return
	
def set_status_text():
	# set the status text based on the results of the last scan
	error_count = 0
	for z in range(0,len(sensors.code),1):
		if sensors.error_number[z] == 0 :
			sensors.status_text[z] = ("{0:.4}".format(sensors.reading[z]))
		else:
			error_count +=1
			if sensors.delay[z] >= config.delay_limit:
				sensors.status_text[z] = ("Wait" + str(int(sensors.delay[z])))
			else:
				sensors.status_text[z] = (error[sensors.error_number[z]])
	
def make_printout_for_screen(datachange):
	global config
	global sensors
	global smartplug_info
	global target_temp
	here = "make_printout_for_screen"
	error_count = 0
	#set printout for start of the line
	printout = str(config.scan_count) + " of " + str(config.max_scans) + " " + datetime.datetime.now().strftime("%d:%m:%Y %H:%M:%S") + " Target: " +  str(target_temp) 
	for z in range(0,len(sensors.code),1):
		if sensors.connected[z]:
			printout += "[" + str(sensors.number[z]) + "=" + sensors.status_text[z] + "]"
		else:
			if sensors.code_seen[z]:
				printout += "[" + str(sensors.number[z]) + "= disconn ]"
	printout += "  "
	#if not datachange:
	#	printout += "[no changes]"
	if max(sensors.delay) >= config.delay_limit:
		printout +="[max delay count:" + "{0:.4}".format(max(sensors.delay)) +"]"
	if len(dropped_list) > 0:
		printout += "[disconnected:" + dropped_list + "]"
	if error_count >0 :
		printout += "[error count=" + str(error_count) +"]"
	if not max(sensors.connected):
		printout += "[no sensors]"
	return(printout)
	
def get_target_temp(year,month,day,hour,minute):
	global schedule
	global config
		
# From Scedule get Target Temperature
			# Search for Target Temp
	target_temp = -100 
	ind_result = 1
	
	for ind in range(1,len(schedule.year)):
		if int(year) == int(schedule.year[ind]):
			if int(month) == int(schedule.month[ind]):
				if int(day) == int(schedule.day[ind]):
					if int(hour) == int(schedule.hour[ind]):
						if int(minute) >= int(schedule.minute[ind]):
							if int(minute) <= int(schedule.minute[ind+1]):
								ind_result = ind
								break
							else:
								ind_result = ind	
	if config.last_target != schedule.target_temp[ind_result+1]:
		pr_status(True,0, " config.last_target : " + str(config.last_target) + "   New Target : " +
				str(schedule.target_temp[ind_result+1]))		
	config.last_target = schedule.target_temp[ind_result+1]

	
	if ind_result == 1:
		pr_status(True,0,"Error or very new schedule >> ind result : " + str(ind_result) + "Target set to 17.654321")
		return (17.654321)
	else:
		if ind_result +1 > len(schedule.year):
			pr_status(True,0,"Error>> ind result : " + ind_result +  "Target set to 16.54321")
			return (16.54321)
		else:
			# remove # in next 4 lines for debug
			#pr_status(True,0,"Schedule Look Up Result>> index used: " + str(ind_result+1).zfill(4) + "  Date : "
			# + str(schedule.year[ind_result+1]).zfill(4) + "/" + str(schedule.month[ind_result+1]).zfill(2) + "/"
			# + str(schedule.day[ind_result+1]).zfill(2) +" Time: " + str(schedule.hour[ind_result+1]).zfill(2) +":" 
			# + str(schedule.minute[ind_result+1]).zfill(2) +" Target : " + str(schedule.target_temp[ind_result+1]))
			return (float(schedule.target_temp[ind_result+1]))
				
	
def main(argv):
	global config
	global starttime
	global sensors
	global schedule
	global debug
	global target_temp
	global status_bffr
	global log_bffr
	global last_ref
	
	last_ref = -1
	
	here = "main"
	#Set things up and read in 
	init(argv) # 6 tasks setting up variables etc
	# if there is a file with sensor data read it in
	if fileexists(config.sensor_info_filename):
		read_in_sensor_data(config.sensor_info_filename)
	
	# if there is a schedule file read it in
	pr_status(True,0,"Loading Schedule File Data from :  " + config.prog_path + "/" + "schedule.csv")
	if fileexists(config.prog_path + "/" + "schedule.csv"):
		schedule = class_schedule()
		read_in_schedule_data(config.prog_path + "/" + "schedule.csv")	
	else:	
		quit ( "No Schedule")
		
	if config.logging_on:
		pr(here, "Starting with Logging to : " + config.logging_filename_save_as + " at ", datetime.datetime.now())
	else:
		pr(here, "Starting with Logging Off at : ", + datetime.datetime.now())
	if config.max_scans > 0:
		pr(here, "Starting Temp Sensor Scans for : " + str(config.max_scans) + " scans starting at : ", datetime.datetime.now())
	else:
		pr(here, "Starting Continuous Temp Sensor Scans for at : ", datetime.datetime.now())
	pr(here, "With an interval of : ", config.scan_delay) 
	
	
 
	#Main Loop
	change_flag = False
	config.scan_count = 1
	config.sensor_present = False
	# Scan for max_scan times or for ever if config.max_scans = 0
	while (config.scan_count <= config.max_scans) or (config.max_scans == 0):
		# check_for_new codes and find out what sensors are cobnnected
		# geting new codes if there are any
		new_codes_count = check_what_is_connected()
		
		# then if there are any new we have not seen before write to the sensor file
		if new_codes_count >0 :
			write_sensor_data(new_codes_count,len(sensors.code) == new_codes_count)

		# now get data from all the sensor that are connected
		for z in range(0,len(sensors.code),1):
			if sensors.connected[z]:
				# if there has been a timeout value will be about 8 initially
				if (sensors.delay[z] < config.delay_limit):
					get_temperature(z)
					pr(here,"sensor : " + str(sensors.number[z]) + " returned :", sensors.reading[z])
				else:
					if sensors.delay[z] >= config.delay_limit:
						sensors.delay[z] -= config.delay_increment # so after few scans will try again
			else:
				sensors.delay[z] = 0
			# check if this sensor has changed more than 0.25 degrees, if so set flag 
			# that will trigger print out and logging 
			if (abs(sensors.last_logged[z] - sensors.reading[z])) > float(config.change4log): 
				change_flag = True
				if config.scan_count > 1 :
					# Following two Lines helps watching changes but is not needed
					# pr_log(True,"Change detected in sensor : " + str(sensors.number[z]) + "was : " +
					# str(sensors.last_logged[z]) + " now : " + str(sensors.reading[z]))
					sensors.last_logged[z] = sensors.reading[z]
			if sensors.last_logged_error_number[z] != sensors.error_number[z]:
				change_flag = True 

# **************************** 
#  Get target temperature
#****************************	
		time_now = datetime.datetime.now()
		target_temp = get_target_temp(time_now.year,time_now.month,time_now.day,time_now.hour,time_now.minute)

# ****************************
# Start of smartplug Control *
# ****************************

		# before operating smartplugs get their status		
		#print ("get sps in log temp data before operate them")
		
		#  Check if reading indictates if heaters should be turned on of off		
		
		if (len(sensors.reading) > 0) and (config.ref_sensor_index != -1 ):
			if sensors.reading[config.ref_sensor_index] > target_temp + float(config.control_hysteresis) :
				turn_off_smartplug(0)
				turn_off_smartplug(1)
			else:
				if sensors.reading[config.ref_sensor_index] < target_temp - float(config.control_hysteresis) :
					turn_on_smartplug(0)
					turn_on_smartplug(1)
		else:
			pr_status(True,0, "Cannot control no sensors or reference sensor not defined")			
		
		# now having operated smartplugs get their status
		# print ("get sps in log temp data after operate them")		
				
# ****************************
#  End  of smartplug Control *
# ****************************

		#for test only to get more print outs and logging
		#change_flag = True

		print ( "FTP Log, Change Flag : ", change_flag, "Count " + str(config.ftplog_count) + " of " + str(config.ftplog), " Logging File names : ", config.ftp_credentials_log_filename +  \
		                                                 " : " +  config.logging_filename + " : " +  config.logging_filename_save_as)
		if change_flag or (config.scan_count == config.max_scans) or (config.scan_count == 0):
			# now if data changed do logging printing and sending
			set_status_text() # figure out the status text for the temperature sensors
			if config.logging_on:
				log_temperature_data_to_file()
			if config.ftplog_count > config.ftplog :
			
				# @@@
				#ftp_result = send_by_ftp(config.ftp_credentials_log_filename, config.logging_filename, config.logging_filename_save_as)
				ftp_result = "1293"
				
				#uncomment following two lines to get info on FTP attempts
				#for pres_ind in range(0,len(ftp_result)):
				#	print (ftp_result[pres_ind])
				
				try:
					copyfile(config.logging_filename, config.local_www_log_csv)
					# uncomment following line for info on copying file to web site dir
					# print ( "Sent : "+ config.logging_filename_save_as + " to : " + config.local_www_log_csv)
				except:
					pr_status(True,0, "Fail with send log csv to " + config.local_www_log_csv)
			
				config.ftplog_count = 0
			
			else:
				config.ftplog_count = config.ftplog_count +1 

# *******************************************************************************
#  After logging done, have all info send html file to websites done every scan *
# *******************************************************************************
		send_temperature_data_using_ftp(config.ftp_credentials_filename)

		if (len(sensors.reading) > 0):
			#must be some sensor before we can print data
			if debug:
				#printouts if in debug
				pr_log(True, "\n" + make_printout_for_screen(change_flag) + "\n")
			else:
				if change_flag:
					#printouts if not in debug and data changed
					pr_log(True,make_printout_for_screen(change_flag))
				else:
					#printouts if not in debug and no data changed
					pr_log(False,make_printout_for_screen(change_flag))
		else:
			pr_status( True,0,0, "No sensors found yet")
			pr_log(False,"No Sensors found yet")
			
#reset change flag and operate delay before next scan
		change_flag = False
		last_ended  = make_time_text(datetime.datetime.now())	
		time.sleep(config.scan_delay)
		config.scan_count += 1
		# following line can be used 
		pr_status(False,1,"Scan " + str(config.scan_count-1) + " ended at  " + last_ended + "  Now Start Scan : " + str(config.scan_count))
		pr(here, " ******** Scan Counting to " + str(config.max_scans) + "  now at scan " , config.scan_count)
	return 0

if __name__ == '__main__':
	main(sys.argv[1:])


