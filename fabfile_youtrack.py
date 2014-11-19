__author__ = 'vmintam'
from cuisine import user_ensure, dir_exists, dir_ensure, mode_sudo, dir_remove
from cuisine import user_remove, user_check, file_write, package_ensure_yum
from cuisine import package_clean_yum, package_update_yum, file_append
from fabric.api import env, hide, sudo, run
from fabric.colors import red, green
from fabric.decorators import with_settings

env.hosts = ['192.168.1.81']
SUDO_USER = 'vmintam'
SUDO_PASS = '13119685'
YOUTRACK_USER = 'youtrack'
YOUTRACK_LINK = 'http://download.jetbrains.com/charisma/youtrack-6.0.12223.jar'
YOUTRACK_NAME = "youtrack-6.0.12223.jar"
WORKING_DIR = "/usr/local/youtrack"


def user_setup(user):
    """ Creates a test the docs user """
    with mode_sudo():
        if user_check(user):
            user_remove(user, rmhome='/home/%s' % user)
        user_ensure(user, home="/home/%s" % user)

    print (green("=================================================="))
    print(red('created %s user' % user))
    print (green("=================================================="))


def working_dir():
    """
    create directory and chmod for this
    :return:
    """
    with mode_sudo():
        if dir_exists(WORKING_DIR):
            dir_remove(WORKING_DIR)
        dir_ensure(WORKING_DIR, mode="755", owner=YOUTRACK_USER,
                   group=YOUTRACK_USER)
    print (green("=================================================="))
    print(red('created %s working directory' % WORKING_DIR))
    print (green("=================================================="))


#===============================================================================
#install epel repository
def install_epel():
    epel_link = 'http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm'
    sudo('rpm -Uvh %s' % epel_link)
    package_clean_yum()
    package_update_yum()
    print (green("=================================================="))
    print (red("installed epel repository"))
    print (green("=================================================="))


def install_req():
    sudo('yum groupinstall -y "Development tools" ; true')
    package_ensure_yum('nginx')


def install_java():
    java_link = 'http://www.reucon.com/cdn/java/jdk-7u51-linux-x64.tar.gz'
    sudo('wget -O /tmp/jdk-7u51-linux-x64.tar.gz %s' % java_link)
    with mode_sudo():
        if dir_exists('/home/youtrack/jdk1.7.0_51'):
            dir_remove('/home/youtrack/jdk1.7.0_51')
    sudo('tar -xvzf /tmp/jdk-7u51-linux-x64.tar.gz -C /home/youtrack')


def write_daemon():
    youtrack_deamon = """
    #! /bin/sh
### BEGIN INIT INFO
# Provides:          youtrack
# Required-Start:    $local_fs $remote_fs
# Required-Stop:     $local_fs $remote_fs
# Default-Start:     2 3 4 5
# Default-Stop:      S 0 1 6
# Short-Description: initscript for youtrack
# Description:       initscript for youtrack
### END INIT INFO

export HOME=/home/youtrack

set -e

PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
NAME=youtrack
SCRIPT=/usr/local/$NAME/$NAME

d_start() {
    su youtrack -l -c "$SCRIPT start"
}

d_stop() {
    su youtrack -l -c "$SCRIPT stop"
}

case "$1" in
  start)
    echo "Starting $NAME..."
    d_start
    ;;
    stop)
    echo "Stopping $NAME..."
    d_stop
    ;;
  restart|force-reload)
    echo "Restarting $NAME..."
    d_stop
    d_start
    ;;
  *)
    echo "Usage: sudo /etc/init.d/youtrack {start|stop|restart}" >&2
    exit 1
    ;;
esac

exit 0
    """
    with mode_sudo():
        file_write('/etc/init.d/youtrack', content=youtrack_deamon)
    sudo("chmod +x /etc/init.d/youtrack")
    sudo("chkconfig --level 2345 youtrack on")


def write_command_run():
    command_run = """
#! /bin/sh

export HOME=/home/youtrack
export JAVA_HOME=/home/youtrack/jdk1.7.0_51

NAME=youtrack
PORT=8112
USR=/usr/local/$NAME
#JAR=$USR/`ls -Lt $USR/*.jar | grep -o "$NAME-[^/]*.jar" | head -1`
JAR="$USR/youtrack-6.0.12223.jar"
LOG=$USR/$NAME-$PORT.log
PID=$USR/$NAME-$PORT.pid

d_start() {
    if [ -f $PID ]; then
        PID_VALUE=`cat $PID`
        if [ ! -z "$PID_VALUE" ]; then
          PID_VALUE=`ps ax | grep $PID_VALUE | grep -v grep | awk '{print $1}'`
          if [ ! -z "$PID_VALUE" ]; then
                exit 1;
          fi
        fi
    fi

    PREV_DIR=`pwd`
    cd $USR
    exec $JAVA_HOME/bin/java -Xmx1g -XX:MaxPermSize=256m  -Djava.awt.headless=true -jar $JAR $PORT >> $LOG 2>&1 &
    echo $! > $PID
    cd $PREV_DIR
}

d_stop() {
    if [ -f $PID ]; then
        PID_VALUE=`cat $PID`
        if [ ! -z "$PID_VALUE" ]; then
            PID_VALUE=`ps ax | grep $PID_VALUE | grep -v grep | awk '{print $1}'`
            if [ ! -z "$PID_VALUE" ]; then
                kill $PID_VALUE
                WAIT_TIME=0
                while [ `ps ax | grep $PID_VALUE | grep -v grep | wc -l` -ne 0 -a "$WAIT_TIME" -lt 2 ]
                do
                    sleep 1
                    WAIT_TIME=$(expr $WAIT_TIME + 1)
                done
                if [ `ps ax | grep $PID_VALUE | grep -v grep | wc -l` -ne 0 ]; then
                    WAIT_TIME=0
                    while [ `ps ax | grep $PID_VALUE | grep -v grep | wc -l` -ne 0 -a "$WAIT_TIME" -lt 15 ]
                    do
                        sleep 1
                        WAIT_TIME=$(expr $WAIT_TIME + 1)
                    done
                    echo
                fi
                if [ `ps ax | grep $PID_VALUE | grep -v grep | wc -l` -ne 0 ]; then
                    kill -9 $PID_VALUE
                fi
           fi
        fi
        rm -f $PID
    fi
}

case "$1" in
    start)
        d_start
    ;;
    stop)
        d_stop
    ;;
    *)
        echo "Usage: $0 {start|stop|restart}" >&2
        exit 1
    ;;
esac

exit 0
    """
    with mode_sudo():
        file_write('%s/%s' % (WORKING_DIR, YOUTRACK_USER), content=command_run)
    sudo('chown %s.%s %s/%s' % (YOUTRACK_USER, YOUTRACK_USER,
                                WORKING_DIR, YOUTRACK_USER))
    sudo('chmod +x %s/%s' % (WORKING_DIR, YOUTRACK_USER))


def get_youtrack():
    sudo('wget -O %s/%s %s' % (WORKING_DIR, YOUTRACK_NAME, YOUTRACK_LINK))
    sudo('chown %s.%s %s/%s' % (YOUTRACK_USER, YOUTRACK_USER,
                                WORKING_DIR, YOUTRACK_NAME))


def nginx_config():
    youtrack_site = '/etc/nginx/sites/youtrack.conf'
    upstream_content = """
    upstream youtrack {
    server 127.0.0.1:8112;
    }
    """
    youtrack_content = """
    server {
        listen 80;
        server_name youtrack.vnpid.com;
        access_log  /var/log/nginx/youtrack.vnpid.log;
	    keepalive_timeout 600s;
	    send_timeout 600s;
        location / {
	        client_max_body_size 100M;
            proxy_pass              http://youtrack;
	        proxy_set_header 	    X-Forwarded-Host $http_host;
            proxy_set_header        X-Real-IP $remote_addr;
	        proxy_set_header 	    X-Forwarded-Proto $scheme;
            proxy_set_header        Host $http_host;
            proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_connect_timeout   600;
            proxy_read_timeout      600;
            proxy_send_timeout      600;
        }
    }
    """
    check_yt = run('cat /etc/nginx/conf.d/upstreams.conf | grep youtrack; true')
    with mode_sudo():
        file_write(youtrack_site, youtrack_content)
        if check_yt.find('youtrack') == -1:
            file_append('/etc/nginx/conf.d/upstreams.conf', upstream_content)
    sudo('/etc/init.d/nginx restart')


def start_youtrack():
    sudo('/etc/init.d/youtrack restart')


def iptable_stop():
    sudo('/etc/init.d/iptables stop')


def disable_selinux():
    pass
    # command = run('cat /etc/selinux/config | grep "SELINUX=disabled"')


@with_settings(hide('running', 'commands', 'stdout', 'stderr'))
def deploy():
    env.user = SUDO_USER
    env.password = SUDO_PASS
    iptable_stop()
    disable_selinux()
    user_setup(YOUTRACK_USER)
    working_dir()
    if sudo('ls -laht /etc/yum.repos.d/ | grep epel ; true').find('epel') != -1:
        print (red("epel have already installed"))
    else:
        install_epel()
    install_req()
    get_youtrack()
    install_java()
    write_daemon()
    write_command_run()
    nginx_config()
    start_youtrack()