#!/bin/sh


echo "development: True" > .projectrc
echo "project_configuration:" >> .projectrc
echo "  variables:" >> .projectrc
echo "    env:" >> .projectrc
echo "      CELERYUI_PASSWORD: test${RANDOM}" >> .projectrc
echo "      CELERYUI_USER: test${RANDOM}" >> .projectrc


