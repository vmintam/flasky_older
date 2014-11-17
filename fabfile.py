from fabric.api import *

class ParallelCommands():
    def __init__(self, **args):
        self.hosts = args['hosts']
        self.command = args['command']

    @parallel(pool_size=10)  # Run on as many as 10 hosts at once
    def parallel_exec(self):
        return run(self.command)

    def capture(self):
        with settings(hide('running', 'commands', 'stdout', 'stderr')):
            stdout = execute(self.parallel_exec, hosts=self.hosts)
        return stdout


def test():
    hosts=['vmintam@192.168.1.215', 'vmintam@210.245.80.197']
    command = 'date'
    instance = ParallelCommands(hosts=hosts, command=command)
    output = instance.capture()
    print output
    """
    The output of each server is inside a dictionary:
    { 'root@server1': 'output', 'root@server2': 'output' }
    """
    # print output['root@server1']