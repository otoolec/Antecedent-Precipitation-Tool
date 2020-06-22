# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING. If not, write to the
# Free Software Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

######################################
##  ------------------------------- ##
##          get_items.py            ##
##  ------------------------------- ##
##     Written by: Jason Deters     ##
##  ------------------------------- ##
##    Last Edited on: 2020-06-11    ##
##  ------------------------------- ##
######################################

# Import Standard Libraries
import os
import sys
import requests
import time
import zipfile

# Find module path
MODULE_PATH = os.path.dirname(os.path.realpath(__file__))
# Find ROOT folder
ROOT = os.path.split(MODULE_PATH)[0]


# Import Custom Libraries
try:
    # Frozen Application Method
    from .utilities import JLog
except Exception:
    # Reverse compatibility method - add utilities folder to path directly
    PYTHON_SCRIPTS_FOLDER = os.path.join(ROOT, 'Python Scripts')
    TEST = os.path.exists(PYTHON_SCRIPTS_FOLDER)
    if TEST:
        UTILITIES_FOLDER = os.path.join(PYTHON_SCRIPTS_FOLDER, 'utilities')
        sys.path.append(UTILITIES_FOLDER)
    else:
        ARC_FOLDER = os.path.join(ROOT, 'arc')
        UTILITIES_FOLDER = os.path.join(ARC_FOLDER, 'utilities')
        sys.path.append(UTILITIES_FOLDER)
    import JLog




def parse_version(version_file_path=None, version_url=None):
    """
    If path is provided, reads file and parses version number
    If url is provided, Uses requests to check the first line of a text file at a URL
    """
    if not version_file_path is None:
        version_file_path = os.path.join(ROOT, 'version')
        with open(version_file_path, 'r') as version_file:
            for line in version_file:
                version_string = line.replace('\n','')
                version_list = version_string.split('.')
                version_major = version_list[0]
                version_minor = version_list[1]
                version_patch = version_list[2]
                break
    if not version_url is None:
        response = requests.get(version_url)
        time.sleep(.1)
        version_string = response.text.replace('\n','')
        version_list = version_string.split('.')
        version_major = version_list[0]
        version_minor = version_list[1]
        version_patch = version_list[2]
    return int(version_major), int(version_minor), int(version_patch)

def extract_to_folder(zip_file, output_folder, pwd=None):
#    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
#        if pwd is None:
#            zip_ref.extractall(output_folder)
#        else:
#            zip_ref.extractall(output_folder, pwd=pwd.encode())
    with zipfile.ZipFile(zip_file) as zip:
        for zip_info in zip.infolist():
            if pwd is None:
                try:
                    zip.extract(zip_info, output_folder)
                except Exception:
                    pass
            else:
                try:
                    zip.extract(zip_info, output_folder, pwd=pwd.encode())
                except Exception:
                    pass


def sizeof_fmt(num, suffix='B'):
    for unit in [' ', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "{:6.2f} {}{}".format(num, unit, suffix)
        num /= 1024.0
    return "{:6.2f} {}{}".format(num, 'Y', suffix)


def ensure_file_exists(file_url, local_file_path, local_check_file=None,
                       version_url=None, version_local_path=None, minimum_size=None,
                       extract_path=None, extract_pwd=None):
    """Checks for file, downloads if necessary"""
    download = False
    local_version = 0
    log = JLog.PrintLog()
    download_dir, file_name = os.path.split(local_file_path)
    # Check for local file
    local_file_exists = os.path.exists(local_file_path)
    if not local_file_exists:
        download = True
    else:
        if minimum_size is not None:
            local_file_size = os.path.getsize(local_file_path)
            if local_file_size < minimum_size:
                log.Wrap('    {} corrupt. Deleting...'.format(local_file_path))
                os.remove(local_file_path)
                download = True
    if download is True:
        # Ensure download directory exists
        try:
            os.makedirs(download_dir)
        except Exception:
            pass
        dl_start = time.clock()
        # Streaming with requests module
        num_bytes = 0
        count = 0
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            with open(local_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
                        num_bytes += 8192
                        count += 1
                        if count > 25:
                            formatted_bytes = sizeof_fmt(num_bytes)
                            log.print_status_message('    Downloading {}... ({})'.format(file_name, formatted_bytes))
                            count = 0
        formatted_bytes = sizeof_fmt(num_bytes)
        log.Wrap('    {} Downloaded ({})'.format(file_name, formatted_bytes))
        sys.stdout.flush()
        time.sleep(.1)
        # Extract compressed package if selected
        if extract_path is None:
            extracted = ''
        else:
            extracted = 'and Extracting '
            log.Wrap('    Extracting package to target directory...')
            extract_to_folder(zip_file=local_file_path,
                              output_folder=extract_path,
                              pwd=extract_pwd)
            log.Wrap('     Extraction complete. Deleting zip file...')
            # Remove zip file after extraction
            os.remove(local_file_path)
        log.Time(dl_start, 'Downloading {}{}'.format(extracted, file_name))
        log.Wrap('')
    return

def get_only_newer_version(file_url, local_file_path, local_check_file=None,
                           version_url=None, version_local_path=None, minimum_size=None,
                           extract_path=None, extract_pwd=None):
    """Checks for file and version, downloads if necessary"""
    download = False
    local_version_major = 0
    local_version_minor = 0
    local_version_patch = 0
    log = JLog.PrintLog()
    download_dir, file_name = os.path.split(local_file_path)
    log.print_section('Checking for updates to {}'.format(file_name))
    # Check Web Version
    if version_url is not None:
        version_dir, version_name = os.path.split(version_local_path)
        web_version_major, web_version_minor, web_version_patch = parse_version(version_url=version_url)
        # If Local File exists Check Local Version
        version_local_file_exists = os.path.exists(version_local_path)
        if version_local_file_exists:
            local_version_major, local_version_minor, local_version_patch = parse_version(version_file_path=version_local_path)
        if download is False:
            # Compare local and web versions
            if web_version_major > local_version_major:
                download = True
            elif web_version_major == local_version_major:
                if web_version_minor > local_version_minor:
                    download = True
                if web_version_minor == local_version_minor:
                    if web_version_patch > local_version_patch:
                        download = True
    if download is True:
        log.Wrap('  Local version = {}.{}.{}'.format(local_version_major, local_version_minor, local_version_patch))
        log.Wrap('  Web version = {}.{}.{}'.format(web_version_major, web_version_minor, web_version_patch))
        # If web newer, delete local and set download to True
        try:
            os.remove(local_file_path)
        except Exception:
            pass
        # Ensure download directory exists
        try:
            os.makedirs(download_dir)
        except Exception:
            pass
        dl_start = time.clock()
        # Streaming with requests module
        num_bytes = 0
        count = 0
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            with open(local_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
                        num_bytes += 8192
                        count += 1
                        if count > 25:
                            formatted_bytes = sizeof_fmt(num_bytes)
                            log.print_status_message('    Downloading {}... ({})'.format(file_name, formatted_bytes))
                            count = 0
        formatted_bytes = sizeof_fmt(num_bytes)
        log.Wrap('    {} Downloaded ({})'.format(file_name, formatted_bytes))
        sys.stdout.flush()
        time.sleep(.1)
        # Extract compressed package if selected
        if extract_path is None:
            extracted = ''
        else:
            extracted = 'and Extracting '
            log.Wrap('    Extracting package to target directory...')
            extract_to_folder(zip_file=local_file_path,
                              output_folder=extract_path,
                              pwd=extract_pwd)
            log.Wrap('     Extraction complete. Deleting zip file...')
            # Remove zip file after extraction
            os.remove(local_file_path)
        # Write new Version file
        log.Wrap('  Updating local version file...')
        version_local_folder = os.path.dirname(version_local_path)
        # Ensure download directory exists
        try:
            os.makedirs(version_local_folder)
        except Exception:
            pass
        if version_url is not None:
            with open(version_local_path, 'w') as version_file:
                version_file.write('{}.{}.{}'.format(web_version_major, web_version_minor, web_version_patch))
        log.Time(dl_start, 'Downloading {}{}'.format(extracted, file_name))
        log.Wrap('')
    return


#if __name__ == '__main__':
#    LOCAL_VERSION = check_local_version(version_local_path=r'D:\Code\Python\WinPythonARC_dev_EPA_dl_dl\core\main_ex_version.txt')
#    print(LOCAL_VERSION)

#    ensure_file_exists(file_url='https://www.spk.usace.army.mil/Portals/12/documents/regulatory/upload/APT/WBD/HUC8_Albers.zip',
#                       local_file_path=r'C:\Users\L2RCSJ9D\Desktop\delete\apt\WBD\zip\HUC8_Albers.zip',
#                       version_url='https://www.spk.usace.army.mil/Portals/12/documents/regulatory/upload/APT/WBD/WBD.txt',
#                       version_local_path=r'C:\Users\L2RCSJ9D\Desktop\delete\apt\versions\WBD.txt',
#                       extract_path=r'C:\Users\L2RCSJ9D\Desktop\delete\apt\WBD')

#    ensure_file_exists(file_url='https://www.spk.usace.army.mil/Portals/12/documents/regulatory/upload/APT/WBD/HUC8_Albers.zip',
#                       local_file_path=r'C:\Users\L2RCSJ9D\Desktop\delete\apt\WBD\zip\HUC10_Albers.zip.001',
#                       version_url='https://www.spk.usace.army.mil/Portals/12/documents/regulatory/upload/APT/WBD/WBD.txt',
#                       version_local_path=r'C:\Users\L2RCSJ9D\Desktop\delete\apt\versions\WBD.txt',
#                       extract_path=r'C:\Users\L2RCSJ9D\Desktop\delete\apt\WBD')

#    ensure_file_exists(file_url='https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/WBD/HU2/Shape/WBD_01_HU2_Shape.zip',
#                       local_file_path=r'C:\Users\L2RCSJ9D\Desktop\delete\apt\WBD\zip\WBD_01_HU2_Shape.zip',
#                       extract_path=r'C:\Users\L2RCSJ9D\Desktop\delete\apt\WBD')

#    version = check_web_version('https://raw.githubusercontent.com/jDeters-USACE/Test_REpo/master/Release/version')
#    print('version = {}'.format(version))
