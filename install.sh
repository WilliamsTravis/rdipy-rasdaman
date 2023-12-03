#!/usr/bin/env bash

# Prints the usage of the script with all the available options
usage(){
cat <<'END_HEREDOC'
DESCRIPTION
    Rasdaman Installer - Install rasdaman based on an installation profile.

OPTIONS
    -h, --help      Displays the usage information of this script
    -j, --profile_path
                    Use the profile at the given path. If set, this option
                    supersedes the -p, --profile option.
    -d, --download-only
                    Use this option if you want to edit the profile before
                    installing. This will only download the installer into a
                    path that will be printed at the end of the script run;
    -o, --download-directory
                    Use this option if you want to download the installer
                    in a specific directory. By default it is downloaded in /tmp/
                    and moved into the rasdaman installation path at the end of
                    script execution.

EXAMPLES
    Print this message:
        ./install.sh -h
    Run the installer with the given profile:
        ./install.sh -j /home/me/someProfile.toml
    Download the installer in the /home/me directory:
        ./install.sh -d -o /home/me/

END_HEREDOC
}

check_error()
{
    if [ "$1" -ne 0 ]; then
        echo "ERROR: $2"
        exit 1
    fi
}

# Reads the arguments from the command line and initialize the global variables
# that will be passed to the other functions
read_args()
{
  local PROFILE_PATH_OPTION=
  local DWD_DIR_OPTION="/tmp/"
  local DWD_ONLY_OPTION=false

  while [[ $# -gt 0 ]]; do
    local key="$1"
    case "${key}" in
      -j|--profile-path)
        PROFILE_PATH_OPTION="$2"
        shift # past argument
        ;;
      -o|--download-directory)
        DWD_DIR_OPTION="$2"
        shift # past argument
        ;;
      -d|--download-only)
        DWD_ONLY_OPTION=true
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option specified: ${1}."
        usage
        exit 1
      ;;
    esac
    shift # past argument or value
  done

  #Conditional options
  readonly ONLY_DOWNLOAD="${DWD_ONLY_OPTION}"

  #Paths for the installer download
  readonly INSTALLER_DOWNLOAD_PARENT_DIRECTORY="${DWD_DIR_OPTION}"
  readonly RASDAMAN_INSTALLER_NAME="rasdaman-installer"
  readonly INSTALLER_URL="https://download.rasdaman.org/installer/${RASDAMAN_INSTALLER_NAME}.zip"
  readonly INSTALLER_LOCATION="${INSTALLER_DOWNLOAD_PARENT_DIRECTORY}/${RASDAMAN_INSTALLER_NAME}"
  readonly INSTALLER_ARCHIVE_DOWNLOAD_LOCATION="${INSTALLER_LOCATION}.zip"

  # Paths for the installer main script
  readonly INSTALLER_PYTHON_MAIN="${INSTALLER_LOCATION}/main.py"

  # Choosing the right profile
  if [ -n "$PROFILE_PATH_OPTION" ] ; then
    readonly INSTALLER_PROFILE=$(readlink -m "${PROFILE_PATH_OPTION}")
  fi
}

# sets PYTHONBIN to python/python2/python3, whichever is available in that order
get_python_binary()
{
  PYTHONBIN=
  for b in python python2 python3; do
    if $b --version > /dev/null 2>&1; then
      PYTHONBIN=$b; break;
    fi
  done
  [ -n "$PYTHONBIN" ]
  check_error $? "python/python2/python3 not found, please install python first."
}

# Checks the minimal dependencies needed to run the installer:
# - wget: needed to download the installer
# - sudo: needed to install extra packages
# - python: needed to run the installer
check_deps(){
  wget --help &> /dev/null
  check_error $? "wget not found, please install it first."

  unzip &> /dev/null
  check_error $? "unzip not found, please install it first."
}

# Downloads the installer
# @param 1: the folder to download the installer to
# @param 2: the url to the installer
# @param 3: the path where the file should be downloaded
download_installer()
{
  cd "${1}"
  check_error $? "The download path '${1}' is not valid."

  wget "${2}" -q --no-check-certificate -O "${3}"
  check_error $? "Could not download the installer."

  unzip -o "${3}" > /dev/null
  check_error $? "Could not unzip the installer."
}

# Runs the installer
# @param 1: the path to the main script
# @param 2: the path to the profile
run_installer(){
  sudo -l > /dev/null
  check_error $? "You need to be able to run the sudo command in order to continue the installation. Check your sudo rights using sudo -l"

  get_python_binary

  sudo "$PYTHONBIN" "${1}" "${2}"
  check_error $? "The installer returned an error code. The installation might not be valid."
}

# Cleans up the tmp directory of any downloaded file
cleanup()
{
  if [ "$ONLY_DOWNLOAD" != true ] ; then
    rm -rf "${INSTALLER_LOCATION}"
  fi
  rm -f "${INSTALLER_ARCHIVE_DOWNLOAD_LOCATION}"
}
trap cleanup EXIT

# Read commandline arguments and decide what to do
read_args "$@"
check_deps

# Choose a default profile (from extracted download installer folder at 
# /tmp/rasdaman-installer) if no other option given
if [ "$#" -eq 0 ]; then
  INSTALLER_PROFILE="${INSTALLER_DOWNLOAD_PARENT_DIRECTORY}/${RASDAMAN_INSTALLER_NAME}/profiles/installer/default.toml"
  echo "Using default profile: $INSTALLER_PROFILE"
fi

# Download the installer
download_installer "${INSTALLER_DOWNLOAD_PARENT_DIRECTORY}" \
  "${INSTALLER_URL}" "${INSTALLER_ARCHIVE_DOWNLOAD_LOCATION}"

# If the user wants to examine the installer first
if [ "$ONLY_DOWNLOAD" = true ] ; then
  echo "Rasdamarun_installer"
  run_installer "${INSTALLER_PYTHON_MAIN}" "${INSTALLER_PROFILE}"
fi
