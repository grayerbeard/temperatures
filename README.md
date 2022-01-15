# Room temperature monitoring and control

### January 2022

Rebuilding the software that had been used in 2018 for room temperature control in 2018.
It will probably take a month or so to get it sorted out.

### Install

I will try to ensure the following is a full set of all needed instructions.

Clone or download into folder /home/pi/temperatures.  Do this at the Terminal by typing this
``` 
mkdir temperatures
git clone https://github.com/grayerbeard/temperatures.git /home/pi/temperatures 
```

Install Tmux using 
```
sudo apt-get install tmux
```

Install  w1thermsensor (which can be used to read in values from temperature sensors.  Recently I changed to using this module but in 2018 read values direct from the relavant system files. So the old version from 2018 did not use it. I expect I will change/update to use it.)
```
pip3 install w1thermsensor
```

Install nginx server.  This sets up a local web server which allows status to be viewed ion local network.  The code generates HTML files which get copied to /var/www/html/. Install using
```
sudo apt install nginx
```

Then make the folder where the html files will be put writeable using
```
sudo chown -R pi /var/www/html/
```

You have several ways of starting the code
* do ((do this first to ensure all dependancies are installed, or to debug any problem after changes)
```
cd /home/pi/temperatures and enter
python3 temperatures.py
```  
* to run code in a tmux session and view its output 
```
cd /home/pi/temperatures
./tmux_start.sh
tmux a
```

* set up to run automatically at reboot by editing rc.local. To do this with the nano editor do: 
```
sudo nano /etc/rc.local
```
        
add before the "exit 0"      
```
sudo -u pi bash /home/pi/temperatures/tmux_start.sh &
```
        
then check rc.local works by doing
``` 
cd /etc
./rc.local
```
        
then when restart Pi the python program should start automatically.
Code runs n a tmux session and you can view it using 
```
tmux a -t temperatures
```
        
or just this if only one tmux session in use
 ```
tmux a
 ```

While you are developing the code it is best to comment out the line in rc.local and run the code direct with the command "python3 temperatures.py".  The problem with tmux sessions is if the code crashes it can be hard to establish why.

### About Temperature Sensors

Click this for a Tutorial about Checking out the interface to temperature sensors.  It does mention it here but if you want to connect multiple sensors you just connect them all in parallel, you only need one resistor.

[R Pi Temp Sensor Tutorial](https://tutorials-raspberrypi.com/raspberry-pi-temperature-sensor-1wire-ds18b20/ "R Pi Temp Sensor Tutorial")

This is the sensor I use:  [Pimorini ds18B20](https://shop.pimoroni.com/products/ds18b20-programmable-resolution-1-wire-digital-thermometer)   it is functionally the same as [PiHut ds18B20](https://thepihut.com/products/ds18b20-one-wire-digital-temperature-sensor).  Both items can be obtained far cheaper on eBay.
