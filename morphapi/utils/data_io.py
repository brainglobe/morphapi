import os
import json
import requests
import yaml
import gzip
import numpy as np


def listdir(fld):
    """
    List the files into a folder with the coplete file path instead of the relative file path like os.listdir.

    :param fld: string, folder path

    """
    if not os.path.isdir(fld):
        raise FileNotFoundError("Could not find directory: {}".format(fld))

    return [os.path.join(fld, f) for f in os.listdir(fld)]


def get_subdirs(folderpath):
    """
        Returns the subfolders in a given folder
    """
    return [f.path for f in os.scandir(folderpath) if f.is_dir()]


def check_file_exists(filepath, raise_error=False):
    # Check if a file with the given path exists already
    if os.path.isfile(filepath):
        return True
    elif raise_error:
        raise FileExistsError("File {} doesn't exist".format(filepath))
    else:
        return False


def get_file_name(filepath):
    # Returns just the name, no complete path or extension
    return os.path.splitext(os.path.basename(filepath))[0]


# ------------------------------ Load/Save data ------------------------------ #
def load_npy_from_gz(filepath):
    f = gzip.GzipFile(filepath, "r")
    return np.load(f)


def save_npy_to_gz(filepath, data):
    f = gzip.GzipFile(filepath, "w")
    np.save(f, data)
    f.close()


def save_json(filepath, content, append=False):
    """
    Saves content to a JSON file

    :param filepath: path to a file (must include .json)
    :param content: dictionary of stuff to save

    """
    if "json" not in filepath:
        raise ValueError("filepath is invalid")

    if not append:
        with open(filepath, "w") as json_file:
            json.dump(content, json_file, indent=4)
    else:
        with open(filepath, "w+") as json_file:
            json.dump(content, json_file, indent=4)


def save_yaml(filepath, content, append=False, topcomment=None):
    """
    Saves content to a yaml file

    :param filepath: path to a file (must include .yaml)
    :param content: dictionary of stuff to save

    """
    if not filepath.endswith(".yaml") and not filepath.endswith(".yml"):
        raise ValueError(
            f"filepath is invalid {filepath}. Should end with yaml or yml"
        )

    if not append:
        method = "w"
    else:
        method = "w+"

    with open(filepath, method) as yaml_file:
        if topcomment is not None:
            yaml_file.write(topcomment)
        yaml.dump(content, yaml_file, default_flow_style=False, indent=4)


def load_json(filepath):
    """
    Load a JSON file

    :param filepath: path to a file

    """
    if not os.path.isfile(filepath) or ".json" not in filepath.lower():
        raise ValueError("unrecognized file path: {}".format(filepath))
    with open(filepath) as f:
        data = json.load(f)
    return data


def load_yaml(filepath):
    """
    Load a YAML file

    :param filepath: path to yaml file

    """
    if filepath is None or not os.path.isfile(filepath):
        raise ValueError("unrecognized file path: {}".format(filepath))
    if "yml" not in filepath and "yaml" not in filepath:
        raise ValueError("unrecognized file path: {}".format(filepath))
    return yaml.load(open(filepath), Loader=yaml.FullLoader)


# ----------------------------- Internet queries ----------------------------- #
def connected_to_internet(url="http://www.google.com/", timeout=5):
    """
        Check that there is an internet connection

        :param url: url to use for testing (Default value = 'http://www.google.com/')
        :param timeout:  timeout to wait for [in seconds] (Default value = 5)
    """

    try:
        _ = requests.get(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        print("No internet connection available.")
    return False


def send_query(query_string, clean=False):
    """
    Send a query/request to a website

    :param query_string: string with query content
    :param clean:  (Default value = False)

    """
    response = requests.get(query_string)
    if response.ok:
        if not clean:
            return response.json()["msg"]
        else:
            return response.json()
    else:
        raise ValueError("Invalide query string: {}".format(query_string))


# ---------------------------------------------------------------------------- #
#                               Data manipulation                              #
# ---------------------------------------------------------------------------- #
def flatten_list(lst):
    """
    Flattens a list of lists
    
    :param lst: list

    """
    flatten = []
    for item in lst:
        if isinstance(item, list):
            flatten.extend(item)
        else:
            flatten.append(item)
    return flatten


def is_any_item_in_list(L1, L2):
    """
    Checks if an item in a list is in another  list

    :param L1: 
    :param L2: 

    """
    # checks if any item of L1 is also in L2 and returns false otherwise
    inboth = [i for i in L1 if i in L2]
    if inboth:
        return True
    else:
        return False
