# import the needed components.
# Allot of people use "from fabric.api import *" It's OK when testing but    \ 
# when creating production worthy scripts import only the needed components. \
# It prevents namespace pollution and makes your scripts easier to read.
# $ python
# Python 2.7.5 (default, Mar  9 2014, 22:15:05)
# [GCC 4.2.1 Compatible Apple LLVM 5.0 (clang-500.0.68)] on darwin
# >>> import base64
# >>> base64.b64encode("verysecretpassword")
# 'dmVyeXNlY3JldHBhc3N3b3Jk'
# >>> base64.b64decode("dmVyeXNlY3JldHBhc3N3b3Jk")
# 'verysecretpassword'
# def install_req(package):
#     command = run("rpm -q %s | grep 'is not installed'; true" % package)
#     if command.find('is not installed') != -1:
#         print "test"
#         run('cat /etc/resolv.conf')
#         run('echo %s' % package)

import base64
from fabric.api import sudo, run, prompt
from fabric.contrib.files import append, sed, upload_template

######################### Env vars #####################
env.hosts = ['host1.example.com,host2.example.com']
env.user = 'arjen'
env.password = base64.b64decode("dmVyeXNlY3JldHBhc3N3b3Jk")
########################################################

def puppetmaster():
    """install a puppetmaster.
    - Setup the puppetlabs repo.
    - Update the host.
    - Install the puppetlabs package.
    - Add the correct puppet master and CA.
    - Switch selinux to permissive mode.
    - Disable the yum autoupdate.
    """
    sudo("rpm -ivh https://yum.puppetlabs.com/el/6/products/x86_64/puppetlabs-release-6-10.noarch.rpm")
    sudo("yum -y -q update")
    sudo("yum -y -q install puppet-3.5.1")
    append('/etc/puppet/puppet.conf', 'server = puppet.example.com', use_sudo=True)
    append('/etc/puppet/puppet.conf', 'ca_server = puppetca.example.com', use_sudo=True)
    sudo("setenforce 0")
    sed('/etc/selinux/config',before='SELINUX=enforcing',after='SELINUX=permissive',use_sudo=True,backup='')
    sed('/etc/sysconfig/yum-autoupdate',before='ENABLED="true"',after='ENABLED="false"',use_sudo=True,backup='')

def puppet():
    """Install a puppet client.
    - Setup puppetlabs repo.
    - update the host.
    - install puppet-3.5.1.
    - Add the correct puppetmaster and CA.
    - Disable the yum autoupdate.
    """
    run("rpm -ivh https://yum.puppetlabs.com/el/6/products/x86_64/puppetlabs-release-6-10.noarch.rpm")
    run("yum -y -q update")
    run("yum -y -q install puppet-3.5.1")
    append('/etc/puppet/puppet.conf', 'server = puppet.example.com', use_sudo=True)
    append('/etc/puppet/puppet.conf', 'ca_server = puppetca.example.com', use_sudo=True)
    sed('/etc/sysconfig/yum-autoupdate',before='ENABLED="true"',after='ENABLED="false"',use_sudo=True,backup='')

def push_key():
    """Push my pubkey to the host."""
    keyfile = '/tmp/arjen.pub'
    run('mkdir -p ~arjen/.ssh && chmod 700 ~arjen/.ssh')
    put('~arjen/.ssh/id_rsa.pub', keyfile)
    run('cat %s >> ~arjen/.ssh/authorized_keys && chmod 600 ~arjen/.ssh/authorized_keys' % keyfile)
    run('chown -R arjen ~arjen/.ssh/')
    run('rm %s' % keyfile)

def int_eth1():
    """Setup an eth1 interface with a static ip address.
    Also add the puppetmaster and CA's internal net ip-address to '/etc/hosts'.
    """
    source_file = '/Users/arjen/src/fabric/tst-client/templates/ifcfg-eth1'
    destination_file = '/etc/sysconfig/network-scripts/ifcfg-eth1'
    prompt("int-ipaddress?",key='myaddr',default='192.168.0.5',validate=r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$")
    upload_template(source_file, destination_file, context=env, mode=0644, use_sudo=True)
    run("ifup eth1")
    append('/etc/hosts', '192.168.0.1    puppetca.example.com', use_sudo=True)
    append('/etc/hosts', '192.168.0.2    puppet.example.com', use_sudo=True)