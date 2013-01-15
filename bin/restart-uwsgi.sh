#!/bin/bash
APP_HOME=`dirname "$0"`/..
cd $APP_HOME
./bin/stop-uwsgi.sh
./bin/start-uwsgi.sh
