### Munin - Network watcher
#### Overview
This script was made to handle the problem of a game container taking too much CPU when idle.
This is suitable for UDP-based protocols and will probably not work very well for TCP.
* When no traffic coming to the container the container is paused using 'docker pause'.
* As soon as any packet is sent to the associated ports the container is unpaused
* It has been tested with Valheim dedicated server. 

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
* Timeout - Time in seconds until the container is paused
* Frequency - How often to check if a container has timed out
* Interfaces - List of interfaces to listen on
* Containers - Docker container names with associated ports and protocols

#### Docker
WIP You can run it as a companion container in your stack. 