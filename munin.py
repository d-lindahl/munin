import netifaces
import signal
import sys
import time
from threading import Timer, Lock

import docker
import pyshark
import yaml


class Munin:
    def __init__(self, config_file_name):
        signal.signal(signal.SIGINT, self.handle_sig)
        signal.signal(signal.SIGQUIT, self.handle_sig)
        signal.signal(signal.SIGTERM, self.handle_sig)

        # defaults
        self.debug = False
        self.verbose = False
        self.timeout = 600
        self.frequency = 300
        # Seems pyshark (or tshark) doesn't handle None as interface very well.
        # Should mean all interfaces according to doc
        self.interfaces = netifaces.interfaces()
        self.ignore_starting = True
        self.containers = {}
        self.port_to_container_dict = {}
        self.lock = Lock()
        self.timer = None
        self.capture = None
        self.config_file_name = config_file_name

        # load config from file
        self.load_configuration()

    def load_configuration(self):
        with open(self.config_file_name, 'r') as config_file:
            config = yaml.load(config_file.read(), Loader=yaml.SafeLoader)
        self.set_if_present(config, 'timeout')
        self.set_if_present(config, 'frequency')
        self.set_if_present(config, 'interfaces')
        self.set_if_present(config, 'ignore_starting')
        self.containers = {}
        self.port_to_container_dict = {}
        client = docker.from_env()
        for container_name, container_ports in config['containers'].items():
            container_dict = {
                'name': container_name,
                'ports': container_ports['ports'],
                'instance': client.containers.get(container_name),
                'paused': False,
                'last_packet': 0
            }
            self.containers[container_name] = container_dict
            for port in container_ports['ports']:
                self.port_to_container_dict[port['port']] = container_name

        if len(self.containers) == 0:
            print('No containers to watch configured')
            sys.exit(1)

    def update(self, pkt):
        if self.lock.acquire(blocking=False):
            try:
                port = pkt.info.split(' ')[2]
                container_name = self.port_to_container_dict[int(port)]
                container = self.containers[container_name]
                container['last_packet'] = time.time()
                if container['paused']:
                    print(f"{container_name}: Packet arriving! Waking up the container!")
                    container['instance'].unpause()
                    container['paused'] = False
            finally:
                self.lock.release()

    def check(self):
        self.lock.acquire()
        try:
            print('Munin is surveying the land:')
            for container_data in self.containers.values():
                print(f"{container_data['name']}: ", end='')
                if self.ignore_starting and Munin.health(container_data['name']) == 'starting':
                    print('Container is starting, skipping.')
                else:
                    container_data['instance'].reload()
                    status = container_data['instance'].status
                    since_last_packet = time.time() - container_data['last_packet']
                    if status == 'running':
                        if since_last_packet > self.timeout:
                            if container_data['last_packet'] == 0:
                                print(f'No packets received since Munin launched. Pausing the container.')
                            else:
                                print(f'No packets received for {round(since_last_packet)}s. Pausing the container.')
                            container_data['instance'].pause()
                            container_data['paused'] = True
                        else:
                            print('Container is active')
                    elif status == 'paused':
                        print('Container is paused')
                    elif status == 'exited':
                        print('Container has exited')
                    elif status == 'restarting':
                        print('Container is restarting')
            self.timer = Timer(self.frequency, self.check)
            self.timer.start()
        finally:
            self.lock.release()

    def start(self):
        print('Munin has arrived!')
        port_parts = []
        for container_data in self.containers.values():
            container_data['instance'].reload()
            container_data['paused'] = container_data['instance'].status == 'paused'
            for port in container_data['ports']:
                port_parts.append(f"({port['protocol']} and dst port {port['port']})")
        bpf_filter = ' or '.join(port_parts)
        self.capture = pyshark.LiveCapture(interface=self.interfaces, bpf_filter=bpf_filter, only_summaries=True)
        self.timer = Timer(self.frequency, self.check)
        self.timer.start()
        self.capture.apply_on_packets(self.update)

    def handle_sig(self, sig, frame):
        del sig, frame
        self.lock.acquire(timeout=1)
        self.timer.cancel()
        print('Munin has departed!')
        sys.exit(0)

    def set_if_present(self, dictionary, key_name):
        if key_name in dictionary:
            setattr(self, key_name, dictionary[key_name])

    @staticmethod
    def health(container_name):
        client = docker.APIClient(base_url='unix://var/run/docker.sock')
        container = client.inspect_container(container_name)
        return container['State']['Health']['Status']


def main(argv):
    config_file_name = 'config.yaml'
    if argv:
        config_file_name = argv[0]
    munin = Munin(config_file_name)
    munin.start()


if __name__ == "__main__":
    main(sys.argv[1:])
