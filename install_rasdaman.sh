#!/bin/bash
# Still working on this only debian based systems will work at the moment. Use
# this if you have a compatible version of Debian or Ubuntu to install
# rasdaman with the apt package manager.

set -e

# Figure out your OS code name
os=$(lsb_release -d)
code=$(lsb_release -c)
osname=$(echo $os | awk '{split($0,s);print s[2]}')
codename=$(echo $code | awk '{split($0,s);print s[2]}')
echo "Installing Rasdaman for $osname, $codename"

# Update your package manager to get all the latest stuff
sudo apt-get upgrade

# Make sure your certificates package is installed and/or up to date
sudo apt-get install ca-certificates

# Add the rasdaman public key to your apt keychain
wget -O - https://download.rasdaman.org/packages/rasdaman.gpg | sudo apt-key add -

# Add the rasdaman repository to apt's list so it knows where to look for rasdaman
echo "deb [arch=amd64] https://download.rasdaman.org/packages/deb jammy stable" \
| sudo tee /etc/apt/sources.list.d/rasdaman.list

# Update your package manager to interpret the last addition (apt, this only works for apt)
sudo apt-get -o Dpkg::Options::="--force-confdef" install -y rasdaman
sudo apt-get update

# Install rasdaman
sudo apt-get install rasdaman

# Start the rasdaman service
source /etc/profile.d/rasdaman.sh

# Add demo data
/opt/rasdaman/bin/rasdaman_insertdemo.sh localhost 7001 $RMANHOME/share/rasdaman/examples/images rasadmin rasadmin

# Sample query to check that rasdaman works
rasql -q 'select c from RAS_COLLECTIONNAMES as c' --out string
