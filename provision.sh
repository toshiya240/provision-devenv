#!/bin/bash -e

script_dir="$(cd $(dirname $0) && pwd)"
cd $script_dir

eval "$(/opt/homebrew/bin/brew shellenv)"
ansible-playbook localhost.yml $@
