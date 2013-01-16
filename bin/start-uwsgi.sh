#!/bin/bash
APP_HOME=`dirname "$0"`/..
cd $APP_HOME
mkdir -p $APP_HOME/logs
uwsgi_python --pidfile /tmp/uwsgi.pid -s /tmp/uwsgi.sock -w main:app -p 1 -M -d ./logs/uwsgi.log
