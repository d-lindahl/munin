import sys
import signal
import time
from threading import Timer, Lock
import pyshark
import docker

# number of seconds without activity before the server is paused
TIMEOUT = 10
# how often the status should be checked in seconds
FREQUENCY = 5


class Munin:
    def __init__(self, interface, port_container_dict):
        self.interface = interface
        self.port_container_dict = port_container_dict
        self.containers = {}
        for value in port_container_dict.values():
            container_dict = {
                'container': docker.from_env().containers.get(value),
                'paused': False,
                'last_package': 0
            }
            self.containers[value] = container_dict
        self.lock = Lock()
        self.timer = None

    def update(self, pkt):
        if self.lock.acquire(blocking=False):
            container_name = self.port_container_dict[pkt.udp.dstport]
            container = self.containers[container_name]
            container['last_package'] = time.time()
            if container['paused']:
                print(f'{container_name}: A warrior is arriving in Valheim! The land awakens from its slumber!')
                container['container'].unpause()
                container['paused'] = False
            self.lock.release()

    def check(self):
        self.lock.acquire()
        print('Munin is surveying the land:')
        for container_name, container_data in self.containers.items():
            print(f'{container_name}: ', end='')
            if Munin.health(container_name) == 'starting':
                print('The world is being created. No information can be gleaned.')
            else:
                container_data['container'].reload()
                status = container_data['container'].status
                time_since_last_package = time.time() - container_data['last_package']
                if status == 'running':
                    if time_since_last_package > TIMEOUT:
                        print('Valheim is devoid of warriors. The land falls into a slumber.')
                        container_data['container'].pause()
                        container_data['paused'] = True
                    else:
                        print('Warriors still prevail in Valheim.')
                elif status == 'paused':
                    print('The land slumbers.')
                elif status == 'exited':
                    print('The world has come to an end.')
                elif status == 'restarting':
                    print('The world is being reborn.')
        self.timer = Timer(FREQUENCY, self.check)
        self.timer.start()
        self.lock.release()

    def start(self):
        print('Munin has arrived!')
        for container_data in self.containers.values():
            container_data['container'].reload()
            container_data['paused'] = container_data['container'].status == 'paused'
            container_data['last_package'] = time.time()

        bpf_filter = 'udp and ' + ' or '.join(self.port_container_dict.keys())
        cap = pyshark.LiveCapture(interface=self.interface, bpf_filter=bpf_filter)

        self.timer = Timer(FREQUENCY, self.check)
        self.timer.start()
        cap.apply_on_packets(self.update)

    def handle_sig(self, sig, frame):
        self.lock.acquire(timeout=1)
        self.timer.cancel()
        print('Munin has departed!')
        sys.exit(0)

    @staticmethod
    def health(container_name):
        client = docker.APIClient(base_url='unix://var/run/docker.sock')
        container = client.inspect_container(container_name)
        return container['State']['Health']['Status']


munin = Munin('enp3s0', {'2458': 'valheim-test'})
signal.signal(signal.SIGINT, munin.handle_sig)
signal.signal(signal.SIGQUIT, munin.handle_sig)
signal.signal(signal.SIGTERM, munin.handle_sig)
munin.start()
