#!/bin/bash

if [[ ! -d /opt/homebrew ]]; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

eval "$(/opt/homebrew/bin/brew shellenv)"

brew install ansible
brew install --cask dropbox

echo "You should sync Dropbox."
