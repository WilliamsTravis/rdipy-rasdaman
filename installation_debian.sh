#!/bin/bash

# Update your package manager to get all the latest stuff
sudo apt-get upgrade

# Make sure your certificates package is installed and/or up to date
sudo apt-get install ca-certificates

# Add the rasdaman public key to your apt keychain
wget -O - https://download.rasdaman.org/packages/rasdaman.gpg | sudo apt-key add -

# Figure out your OS code name
code=$(lsb_release -c)
codename=$(echo $code | awk '{split($0,s);print s[2]}')

# Add the rasdaman repository to apt's list so it knows where to look for rasdaman
echo "deb [arch=amd64] https://download.rasdaman.org/packages/deb $codename stable" \
| sudo tee /etc/apt/sources.list.d/rasdaman.list

# Update your package manager to interpret the last addition (apt, this only works for apt)
apt-get -o Dpkg::Options::="--force-confdef" install -y rasdaman
sudo apt-get update

# Install rasdaman
sudo apt-get install rasdaman

# Check that it worked
source /etc/profile.d/rasdaman.sh
