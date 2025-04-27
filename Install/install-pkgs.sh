#!/bin/bash

pkgs=(libsdl2-ttf-2.0-0 libsdl2-image-2.0-0)

sudo pip install pygame --upgrade

sudo apt-get -y --ignore-missing install "${pkgs[@]}" 