# Room temperature monitoring and control

### January 2022

Rebuilding the software that had been used in 2018 for room temperature control in 2018.
It will probably take a month or so to get it sorted out.

### Install

I will try to ensure the following is a full set of all needed instructions.

Clone or download into folder /home/pi/temperatures.  Do this at the Terminal by typing this
'git clone https://github.com/grayerbeard/temperatures.git /home/pi/temperatures".

Install Tmux using 

'sudo apt-get install tmux'

Install  w1thermsensor (which is used to read in the temperature sensor(s))can be used to read in values from temperature sensors.  I have used this module and also read direct. The old version from 2018 di not use it. I expect I will change/update to use it.

'pip3 install w1thermsensor'

Install nginx server.  This sets up a local web server which allows status to be viewed ion local network.  The code generates HTML files which get copied to /var/www/html/. Install using

'sudo apt install nginx'

Then make the folder where the html files will be put writeable using

'sudo chown -R pi /var/www/html/'

You have several ways of starting the code
* go to /home/pi/temperatures and enter 'python3 temperatures.py'  (do that first to ensure all dependancies are installed, or to debug any problem after changes)
* go to /home/pi/temperatures and enter './tmux_start.sh' ((then view code output using 'tmux a')
* set up to run automatically at reboot (then view code output using 'tmux a') by editing rc.local to do the autostart by calling the '/home/pi/temperatures/tmux_start.sh' bash file.
        enter: 'sudo nano /etc/rc.local'
        add before the "exit 0" this      'sudo -u pi bash /home/pi/temperatures/tmux_start.sh &'  
        then check rc.local works by going to /etc folder and entering './rc.local'
        then when restart Pi the python program should start automatically.
        Code is now running in a tmux session and you can view it using 'tmux a -t temperatures'

While you are developing the code it is best to comment out the line in rc.local and run the code direct with the command "python3 temperatures.py".  The problem with tmux sessions is if the code crashes it can be hard to establish why.
