#!/bin/bash
# Still working on this only debian based systems will work at the moment
# Use this to build Rasdaman if the apt installation doesn't work or isn't
# an option

# It is suggested to build rasdaman with a dedicated user, so try running the
# following commands before running this script:
# sudo adduser rasdaman
# sudo -u rasdaman -i

# Stop on errors
set -e

# Figure out your OS code name
os=$(lsb_release -d)
code=$(lsb_release -c)
osname=$(echo $os | awk '{split($0,s);print s[2]}')
codename=$(echo $code | awk '{split($0,s);print s[2]}')
echo "Installing Rasdaman for $osname, $codename"

# Set storage path
export RMANHOME=/opt/rasdaman
sudo mkdir -p $RMANHOME
# sudo chown rasdaman: $RMANHOME

# To build rasdaman
# libgrib2c-dev appears to be deprecated, trying libg2c-dev instead
sudo apt install -y --no-install-recommends make libtool gawk autoconf automake \
pkg-config bison flex git g++ unzip libpng-dev libjpeg-dev libtiff-dev \
libgdal-dev libnetcdf-dev libeccodes-dev libboost-filesystem-dev libssl-dev \
libboost-thread-dev libboost-system-dev libboost-dev zlib1g-dev libffi-dev \
libedit-dev libreadline-dev libdw-dev libsqlite3-dev libg2c-dev \
curl

# To build Java components
sudo apt install -y default-jdk-headless maven ant

# To generate HTML/PDF and C++ API documentation
sudo apt install -y latexmk tex-gyre python3-sphinx python3-sphinx-rtd-theme \
texlive-latex-base texlive-fonts-recommended texlive-latex-extra doxygen

# To run rasdaman
sudo apt install -y sqlite3 zlib1g libdw1 debianutils sudo libssl3 gdal-bin \
libnetcdf-dev libgdal-dev libeccodes0 libreadline-dev libedit-dev \
python3-jsonschema python3-dateutil python3-lxml python3-grib python3-numpy \
python3-netcdf4 python3-pyproj

# To run Java components
sudo apt install -y postgresql postgresql-contrib default-jre-headless

# To run systemtest
sudo apt install -y bc vim-common valgrind netcdf-bin gdal-bin python3-protobuf \
python3-pip jq
pip3 install grpcio pylint==2.13.4 --break-system-packages

# Get Ubuntu dependent files
sudo curl --create-dirs -o /usr/share/java/gdal.jar https://download.rasdaman.org/installer/tpinstaller/ubuntu2204/gdal.jar
sudo curl --create-dirs -o /usr/lib/jni/libgdalalljni.so https://download.rasdaman.org/installer/tpinstaller/ubuntu2204/libgdalalljni.so

# Get Git repository
repo=git://rasdaman.org/rasdaman.git
echo "Cloning $repo to $RMANHOME/rasdaman..."
cd $RMANHOME
if [ ! -d "$RMANHOME/rasdaman" ]; then
    sudo git clone git://rasdaman.org/rasdaman.git
fi
# sudo chown -R $USER: rasdaman
cd rasdaman

# Build Rasdaman
echo "Building Rasdaman in $RMANHOME/rasdaman..."
sudo mkdir -p build/
cd build
sudo cmake .. -DC_MAKE_INSTALL_PREFIX=$RMANHOME -DGENERATE_PIC=yes \
-DUSE_GRIB=yes -DUSE_HDF4=yes -DUSE_NETCDF=yes \
-DUSE_TIFF=yes -DUSE_PNG=yes -DUSE_JPEG=yes -DENABLE_JAVA=yes
sudo make -j8
sudo make install

# Export paths
export RMANHOME=/opt/rasdaman
export PATH=$RMANHOME/bin:$PATH

# Add paths to .bashrc
lines=("# Rasdaman paths" "export RMANHOME=/opt/rasdaman" "export PATH=\$RMANHOME/bin:\$PATH")
for line in "${lines[@]}"
do
    i=$(grep -wn "$line" ~/.bashrc | cut -d: -f1)
    if [ ! -z "$i" ]; then
        b="d"
        id="$i$b"
        sed -i $id ~/.bashrc
    fi
    echo $line >> ~/.bashrc
done

# Create rasdaman database
sudo su postgres && dropuser rasdaman &
sudo -u postgres createuser -s rasdaman

# Create petascope database
echo "Find/set password in $RMANHOME/etc/petascope.properties"
sudo -u postgres createuser -s petauser -P

# Create database and start Rasdaman
cd bin
./create_db.sh
sudo chmod uo+rwx $RMANHOME/log
./start_rasdaman.sh  # Might have to copy petascope.properties to $RMANHOME/data/secore first

# Add demo database
./rasdaman_insertdemo.sh localhost 7001 $RMANHOME/share/rasdaman/examples/images rasadmin rasadmin

# Check that it worked
rasql -q "select r from RAS_COLLECTIONNAMES as r" --out string
