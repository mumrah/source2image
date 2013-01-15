#!/bin/bash
APP_HOME=`dirname "$0"`/..
cd $APP_HOME
uwsgi_python --stop /tmp/uwsgi.pid
