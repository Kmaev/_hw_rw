import os
import hou
from cloud import gd_upload_pyDrive
from cloud import gd_download_pyDrive
import importlib
import json

importlib.reload(gd_upload_pyDrive)
importlib.reload(gd_download_pyDrive)


def get_project_data(node):
    """Gets project name from houdini env or
    if the env variable not defined uses the user input value from project parm.
    Project name is the same as Google Drive folder name where files are going to be uploaded

    Args:
        node: houdini publish HDA node
    Returns:
        project_name

    """
    project_name = os.environ.get("PROJECT_NAME")
    if project_name is None:
        project_name = node.parm("project").evalAsString()
    return project_name


def get_filefolder_data(node):
    """Gets file folder, if folder doesn't exists, create it
    Args:
        node: houdini publish HDA node
    Returns:
        file folder path
    """

    cache_folder = node.parm("basedir").evalAsString()
    cache_name = node.parm("basename").evalAsString()

    version = get_version(node, cache_folder, cache_name)

    file_folder = "{}/{}/v{}".format(cache_folder, cache_name, version)
    _file_dir = os.path.normpath(file_folder)
    _file_dir.replace("/", r"\\")

    if not os.path.exists(_file_dir):
        os.makedirs(file_folder, exist_ok=True)
    return file_folder


def get_version(node, cache_folder, cache_name):
    """Gets version, checking based on listing the folder on disk
    Args:
        node: houdini publish HDA node
        cache_folder: path to cache folder
        cache_name: str cache name
    Returns:
        file version
    """
    auto_versioning = node.parm("autoversion").eval()
    if auto_versioning:
        file_version = node.parm("version").eval() + 1
        _version_folder = "{}/{}".format(cache_folder, cache_name)

        if _version_folder:
            _version_dir = os.listdir(_version_folder)
            if len(_version_dir):
                versions = []
                for _version in _version_dir:
                    versions.append((int(_version.replace("v", ""))))

                file_version = max(versions)
                file_version += 1
            else:
                file_version = 1
    else:
        file_version = node.parm("version").eval()

    return file_version


def get_frame_range(node):
    """Gets frame range
    Args:
        node: houdini publish HDA node

    Returns:
        list with start and end frame
    """
    sim_type = node.parm("trange").eval()
    if sim_type == 0:
        return [hou.frame()]
    if sim_type == 1:
        start_frame = node.parm("f1").eval()
        end_frame = node.parm("f2").eval()
        return [start_frame, end_frame]


def write_metadata(project_name, cache_name, version, frames, file_type):
    """Writes metadata json files
    Args:
        project_name: project name same as google drive folder
        cache_name: file name sources from HDA
        version: cache version sources from HDA
        frames: frame range sources from HDA
        file type: file type sources from HDA

    Returns:

    """
    # The way how json file path sources is temp, it will be added to env
    script_directory = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_directory, "published_assets_metadata.json")

    with open(json_file, "r") as read_file:
        read = json.load(read_file)
    if project_name not in read:
        read[project_name] = {project_name: {}}
    if cache_name not in read[project_name]:
        read[project_name] = {cache_name: {"versions": {}}}

    if version not in read[project_name][cache_name]["versions"]:
        read[project_name][cache_name]["versions"] = {version: {"frames": frames, "type": file_type}}
    else:
        if version in read[project_name][cache_name]["versions"]:
            text = "Version already exists, do you want to overwrite it?"
            user_response = hou.ui.displayMessage(text, buttons=("Overwrite", "Cancel"))
            if user_response == 0:
                read[project_name][cache_name]["versions"] = {version: {"frames": frames, "type": file_type}}
            if user_response == 1:
                raise RuntimeError("Component already exists")

    with open(json_file, "w") as output_file:
        json.dump(read, output_file, indent=4)

    print(read)


def create_path_to_download(project_name, cache_name, version):
    # The way how json file path sources is temp it will be added to env
    """Creates path where files from Google Drive are going to be downloaded
    Args:
        project_name: project name same as google drive folder
        cache_name: file name sources from HDA
        version: cache version sources from HDA

    Returns:

    """
    script_directory = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_directory, "published_assets_metadata.json")
    with open(json_file, "r") as read_file:
        read = json.load(read_file)
    if project_name in read:
        if cache_name in read[project_name]:
            if version in read[project_name][cache_name]["versions"]:
                hip_path = os.environ.get("HIP")

                file_folder = "{}/geo/{}/v{}/".format(hip_path, cache_name, version)
                _file_dir = os.path.normpath(file_folder)
                _file_dir.replace("/", r"\\")

                if not os.path.exists(_file_dir):
                    os.makedirs(file_folder, exist_ok=True)
                return file_folder

            else:
                print("Cache doesn't exist")


def get_cache_name(node):
    """Gets cache name
    Args:
        node: houdini publish HDA node
    Returns:
        cache name str
    """
    cache_name = node.parm("basename").evalAsString()
    return cache_name


def get_file_type(node):
    """Gets file type
    Args:
        node: houdini publish HDA node
    Returns:
        file type str
    """
    parm = node.parm("filetype")
    current_value = parm.eval()
    menu_values = parm.menuItems()
    file_type = menu_values[current_value]
    return file_type


def upload_to_drive(node):
    """upload files to drive, writes metadata json
    Args:
        node: houdini publish HDA node
    Returns:
    """
    file_folder = get_filefolder_data(node)
    project_name = get_project_data(node)
    cache_name = get_cache_name(node)
    version = str(int(get_version(node, file_folder, cache_name)))
    frames = get_frame_range(node)
    file_type = get_file_type((node))
    write_metadata(project_name, cache_name, version, frames, file_type)
    for file in os.listdir(file_folder):

        f = gd_upload_pyDrive.upload_gd(project_name, file, file_folder)
        f.upload()


def download_from_drive(node):
    """download files from drive
    Args:
        node: houdini publish HDA node
    Returns:
    """
    file_folder = get_filefolder_data(node)
    project_name = get_project_data(node)
    cache_name = get_cache_name(node)
    version = str(int(get_version(node, file_folder, cache_name)))
    file_type = get_file_type(node)
    hip_path = os.environ.get("HIP")
    dest_folder = create_path_to_download(project_name, cache_name, version)

    script_directory = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_directory, "published_assets_metadata.json")
    with open(json_file, "r") as read_file:
        read = json.load(read_file)
    frames = read[project_name][cache_name]["versions"][version]["frames"]
    for frame in range(int(frames[0]), int(frames[1] + 1)):
        frame = str(frame).zfill(4)
        file_to_download = "{}_v{}.{}{}".format(cache_name, version, frame, file_type)
        f = gd_download_pyDrive.download_gd(project_name, file_to_download, dest_folder)
        f.download()
