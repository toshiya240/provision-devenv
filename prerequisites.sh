#!/bin/bash

if [[ ! -d /usr/local/Homebrew ]]; then
    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
fi

brew install ansible
brew tap caskroom/cask
brew cask install dropbox

echo "You should sync Dropbox."
