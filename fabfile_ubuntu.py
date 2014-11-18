from cuisine import (user_ensure, dir_ensure, user_passwd, package_ensure,
    run, package_update_apt, package_update, dir_exists, file_link, file_exists,
    repository_ensure_apt)
from fabric.context_managers import cd
from fabric.contrib.files import sed
from fabric.decorators import hosts
from fabric.state import env
from fabric.utils import warn
from fabric.api import sudo, run

HOSTS=['192.168.1.81']  # script doesn't support multiple hosts

SUDO_USER='vmintam'
SUDO_PASS='13119685'

YOUTRACK_USER='rtd_user'
YOUTRACK_PASS='rtd_pass_123'

YOUTRACK_LINK='http://download.jetbrains.com/charisma/youtrack-6.0.12124.jar'
YOUTRACK_NAME="youtrack-6.0.12124.jar"

JDK_LINK='http://www.reucon.com/cdn/java/jdk-7u51-linux-x64.tar.gz'
JDK_NAME='jdk-7u51-linux-x64.tar.gz'

@hosts(HOSTS)
def stage_rtd():
    user_setup()
    java_setup()
    package_setup()
    configure_database()
    project_layout()
    make_virtualenv()
    bootstrap_virtualenv()
    link_django_settings()
    host_replace()
    link_nginx()
    link_supervisor()
    system_prep()


@hosts(HOSTS)
def user_setup():
    """ Creates a read the docs user """
    env.user=SUDO_USER
    env.password=SUDO_PASS

    user_ensure(RTD_USER, home='/opt/rtd')
    user_passwd(RTD_USER, RTD_PASS )

@hosts(HOSTS)
def package_setup(use_db_backend=True):
    """ Install all the required packages """
    env.user=ROOT_USER
    env.password=ROOT_PASS

    # for ppa use
    package_update_apt()
    package_update()
    package_ensure('python-software-properties')
    repository_ensure_apt("-y ppa:nginx/stable") # no prompt

    package_update_apt()
    package_update()

    # to get the most up to date nginx
    package_ensure("supervisor")
    package_ensure("nginx")
    package_ensure("git-core gitosis")
    package_ensure("python-pip python-dev build-essential")
    run("aptitude install memcached -y")

    # TODO: This isn't very idempotent
    # As seen in:
    #   https://bitbucket.org/kmike/django-fab-deploy/src/1e9b66839da6/fab_deploy/db/mysql.py
    if use_db_backend:
        version='5.1'
        passwd='changeme123'
        run('aptitude install -y debconf-utils')

        debconf_defaults = [
            "mysql-server-%s mysql-server/root_password_again password %s" % (version, passwd),
            "mysql-server-%s mysql-server/root_password password %s" % (version, passwd),
            ]

        run("echo '%s' | debconf-set-selections" % "\n".join(debconf_defaults))

        warn('\n=========\nThe password for mysql "root" user will be set to "%s"\n=========\n' % passwd)
        run('aptitude install -y mysql-server')
    package_ensure("libmysqlclient-dev") # for mysql

    run("easy_install pip")
    run("pip install virtualenv")
    run("pip install virtualenvwrapper")

@hosts(HOSTS)
def configure_database(use_db_backend=True):
    """ creates the database """
    env.user=RTD_USER
    env.password=RTD_PASS

    if use_db_backend:
        run("mysql -u root -p'changeme123' -e \"%s\"" % (CREATE_DB_SQL % {'db_name': 'readthedocs'} ))
        try:
            run("mysql -u root -p'changeme123' readthedocs -e \"%s\"" % (DELETE_USER_SQL % { 'db_user': 'readthedocs_user'}))
        except:
            pass # may fail the first time through
        run("mysql -u root -p'changeme123' readthedocs -e \"%s\"" % (CREATE_USER_SQL % { 'db_user': 'readthedocs_user', 'db_password': 'readthedocs_pass_123'}))
        run("mysql -u root -p'changeme123' -e \"%s\"" % (GRANT_PERMISSIONS_SQL % { 'db_user': 'readthedocs_user', 'db_name': 'readthedocs'}))


@hosts(HOSTS)
def project_layout():
    """ Makes project directories """
    env.user=RTD_USER
    env.password=RTD_PASS

    dir_ensure("/opt/rtd/apps/readthedocs", recursive=True)
    dir_ensure("/opt/rtd/htdocs")
    dir_ensure("/opt/rtd/tmp")
    dir_ensure("/opt/rtd/logs")

@hosts(HOSTS)
def make_virtualenv():
    """ builds project in virtual environment """
    env.user=RTD_USER
    env.password=RTD_PASS

    # build the virtualenv
    with cd("/opt/rtd/apps/readthedocs"):
        if not dir_exists("/opt/rtd/apps/readthedocs/%s" % RTD_INITIAL_VERSION):
            run("virtualenv %s" % RTD_INITIAL_VERSION)
        if not dir_exists("/opt/rtd/apps/readthedocs/current"):
            file_link("/opt/rtd/apps/readthedocs/%s" % RTD_INITIAL_VERSION, "/opt/rtd/apps/readthedocs/current")

    # clone the repo
    with cd("/opt/rtd/apps/readthedocs/%s" % RTD_INITIAL_VERSION):
        if not dir_exists("/opt/rtd/apps/readthedocs/%s/%s" % (RTD_INITIAL_VERSION, RTD_CLONE_NAME)):
            run("git clone %s %s" % ( RTD_CLONE, RTD_CLONE_NAME) )

@hosts(HOSTS)
def bootstrap_virtualenv():
    """ install required packages """
    env.user=RTD_USER
    env.password=RTD_PASS

    run("source /opt/rtd/apps/readthedocs/current/bin/activate && pip install -r /opt/rtd/apps/readthedocs/current/readthedocs.org/pip_requirements.txt")
    run("source /opt/rtd/apps/readthedocs/current/bin/activate && /opt/rtd/apps/readthedocs/current/readthedocs.org/readthedocs/manage.py syncdb --noinput --settings=settings.prod")
    run("source /opt/rtd/apps/readthedocs/current/bin/activate && /opt/rtd/apps/readthedocs/current/readthedocs.org/readthedocs/manage.py migrate --noinput --settings=settings.prod")
    run("source /opt/rtd/apps/readthedocs/current/bin/activate && /opt/rtd/apps/readthedocs/current/readthedocs.org/readthedocs/manage.py collectstatic --noinput --settings=settings.prod")
    run("source /opt/rtd/apps/readthedocs/current/bin/activate && /opt/rtd/apps/readthedocs/current/readthedocs.org/readthedocs/manage.py create_api_user --settings=settings.prod")

@hosts(HOSTS)
def link_django_settings():
    """ links the django settings file for the current env """
    with cd("/opt/rtd/apps/readthedocs/current/readthedocs.org/readthedocs/settings"):
        if not file_exists("currentenv.py"):
            file_link("prod.py","currentenv.py")

@hosts(HOSTS)
def host_replace():
    """ replace the host params variables
    """
    sed("/opt/rtd/apps/readthedocs/current/readthedocs.org/conf/nginx.conf", '<% HOST_IP %>', HOSTS[0])
    sed("/opt/rtd/apps/readthedocs/current/readthedocs.org/readthedocs/settings/prod.py", '<% HOST_IP %>', HOSTS[0])

@hosts(HOSTS)
def link_nginx():
    # TODO: would be better as sudo
    env.user=ROOT_USER
    env.password=ROOT_PASS

    if not file_exists("/etc/nginx/sites-enabled/rtf.conf"):
        with cd("/etc/nginx/sites-enabled"):
            file_link("/opt/rtd/apps/readthedocs/current/readthedocs.org/conf/nginx.conf", "rtf.conf")

@hosts(HOSTS)
def link_supervisor():
    # TODO: would be beter as sudo
    env.user=ROOT_USER
    env.password=ROOT_PASS

    if not file_exists("/etc/supervisor/conf.d/rtf.conf"):
        with cd("/etc/supervisor/conf.d"):
            file_link("/opt/rtd/apps/readthedocs/current/readthedocs.org/conf/supervisor.conf", "rtf.conf")


@hosts(HOSTS)
def system_prep():
    """ pre-req process startup """
    env.user=ROOT_USER
    env.password=ROOT_PASS

    run("/etc/init.d/nginx restart")
    run("supervisorctl reload")