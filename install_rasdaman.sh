#!/bin/bash
# Still working on this only debian based systems will work at the moment

# Figure out your OS code name
os=$(lsb_release -d)
code=$(lsb_release -c)
osname=$(echo $os | awk '{split($0,s);print s[2]}')
codename=$(echo $code | awk '{split($0,s);print s[2]}')
echo "Installing Rasdaman for $osname, $codename"


# Certain Debian and Ubuntu systems may install from apt, need to check versions
if [[ $osname == "Debian" || $osname == "Ubuntu" ]]; then

    # Update your package manager to get all the latest stuff
    sudo apt-get upgrade

    # Make sure your certificates package is installed and/or up to date
    sudo apt-get install ca-certificates

    # Add the rasdaman public key to your apt keychain
    wget -O - https://download.rasdaman.org/packages/rasdaman.gpg | sudo apt-key add -

    # Add the rasdaman repository to apt's list so it knows where to look for rasdaman
    echo "deb [arch=amd64] https://download.rasdaman.org/packages/deb $codename stable" \
    | sudo tee /etc/apt/sources.list.d/rasdaman.list

    # Update your package manager to interpret the last addition (apt, this only works for apt)
    apt-get -o Dpkg::Options::="--force-confdef" install -y rasdaman
    sudo apt-get update

    # Install rasdaman
    sudo apt-get install rasdaman

    # Start the rasdaman service
    source /etc/profile.d/rasdaman.sh

    # Add demo data
    /opt/rasdaman/bin/rasdaman_insertdemo.sh localhost 7001 $RMANHOME/share/rasdaman/examples/images rasadmin rasadmin

    # Sample query to check that rasdaman works
    rasql -q 'select c from RAS_COLLECTIONNAMES as c' --out string

else
    # Create a dedicated user
    # sudo adduser rasdaman
    # sudo -u rasdaman -i

    # Set storage path
    export RMANHOME=/opt/rasdaman
    sudo mkdir -p $RMANHOME
    sudo chown rasdaman: $RMANHOME

    # To build rasdaman
    sudo apt install -y --no-install-recommends make libtool gawk autoconf automake \
    pkg-config bison flex git g++ unzip libpng-dev libjpeg-dev libtiff-dev \
    libgdal-dev libnetcdf-dev libeccodes-dev libboost-filesystem-dev libssl-dev \
    libboost-thread-dev libboost-system-dev libboost-dev zlib1g-dev libffi-dev \
    libedit-dev libreadline-dev libdw-dev libsqlite3-dev libgrib2c-dev curl

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
    pip3 install grpcio pylint==2.13.4

    # Get Ubuntu dependent files
    sudo wget curl -nc -O /usr/share/java/gdal.jar https://download.rasdaman.org/installer/tpinstaller/ubuntu2204/gdal.jar
    sudo wget curl -nc -O /usr/lib/jni/libgdalalljni.so https://download.rasdaman.org/installer/tpinstaller/ubuntu2204/libgdalalljni.so

    # Get Git repository
    repo=git://rasdaman.org/rasdaman.git
    echo "Cloning $repo to $RMANHOME/rasdaman..."
    cd $RMANHOME
    if [ ! -d "$RMANHOME/rasdaman" ]; then
        sudo git clone git://rasdaman.org/rasdaman.git
    fi
    # sudo chown -R $USER: rasdaman
    git checkout v9.8.1

    # Build Rasdaman - What's this petascope and secore about?
    echo "Building Rasdaman in $RMANHOME/rasdaman..."
    cd rasdaman
    sudo mkdir -p build/
    cd build
    sudo cmake .. -DC_MAKE_INSTALL_PREFIX=$RMANHOME -DDEFAULT_BASEDB=sqlite \
    -DGENERATE_PIC=yes -DUSE_GRIB=yes -DUSE_HDF4=yes -DUSE_NETCDF=yes \
    -DUSE_TIFF=yes -DUSE_PNG=yes -DUSE_JPEG=yes -DENABLE_JAVA=off
    sudo make -j2
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

    # Create relational database
    sudo su postgres && dropuser rasdaman &
    sudo -u postgres createuser -s rasdaman
    cd bin
    ./create_db.sh

    # Start Rasdaman
    sudo chmod uo+rwx $RMANHOME/log
    ./start_rasdaman.sh

    # Add demo database
    ./rasdaman_insertdemo.sh localhost 7001 $RMANHOME/share/rasdaman/examples/images rasadmin rasadmin

    # Check that it worked
    rasql -q "select r from RAS_COLLECTIONNAMES as r" --out string
fi
