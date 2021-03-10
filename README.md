### Munin - Network watcher
#### Overview
This script was made to handle the problem of a game container taking too much CPU when idle.
This is suitable for UDP-based protocols and will probably not work very well for TCP.
* When no packets are coming to the container the container is paused using 'docker pause'.
* As soon as any packet is sent to the associated ports the container is unpaused
* It has been tested with Valheim dedicated server.**

** Note that, in the case of Valheim, the server of course wont be able to listen to any external status queries unless you're monitoring the query port as well in which case the container will probably be awake most of the time anyway.  


#### Parameters
Munin takes a single parameter specifying the config-file. Default is 'config.yaml' in the same directory as the script.
```shell script
python3 munin.py <path to config file>
```

#### Config
```yaml
timeout: 600
frequency: 300
interfaces:
  - eth0
  - eth1
containers:
  container-one:
    ports:
      - port: 4567
        protocol: udp
      - port: 4568
        protocol: udp
  container-two:
    ports:
      - port: 5678
        protocol: tcp
```
* Timeout - Time in seconds until the container is paused. Default 10 minutes.
* Frequency - How often to check if a container has timed out. Default every 5 minutes.
* Interfaces - List of interfaces to listen on. Leave out for all interfaces.
* Containers - Docker container names with associated ports and protocols

#### Docker
If you run it in docker it needs to run with host network and of course mount the docker.sock.
The configuration should be mounted in /config/munin.yaml
```shell script
docker run --network host -v /var/run/docker.sock:/var/run/docker.sock -v ${PWD}/config.yaml:/config/munin.yaml quaan/munin:latest
```
```docker-compose
version: "3"
services:
  munin:
    image: quaan/munin:latest
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /home/user/munin.yaml:/config/munin.yaml
    network: host
  ...
```