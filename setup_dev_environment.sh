#!/bin/bash

# Dev environment setup for Ubuntu.
sudo apt update
sudo apt -y install python3-opencv
sudo apt -y install libzbar0
sudo apt -y install python3-pip

# install pyhon library
pip3 install pyzbar
pip3 install isodate
pip3 install configparser
