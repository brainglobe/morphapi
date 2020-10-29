import os
import requests
import yaml


def listdir(fld):
    """
    List the files into a folder with the coplete file path instead of the relative file path like os.listdir.

    :param fld: string, folder path

    """
    if not os.path.isdir(fld):
        raise FileNotFoundError("Could not find directory: {}".format(fld))

    return [os.path.join(fld, f) for f in os.listdir(fld)]


def get_file_name(filepath):
    # Returns just the name, no complete path or extension
    return os.path.splitext(os.path.basename(filepath))[0]


# ------------------------------ Load/Save data ------------------------------ #


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
