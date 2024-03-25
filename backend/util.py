import re
import os


def path_exists(path):
    if not os.path.exists(path):
        print(f"{path} does not exist!")
        return False
    return True


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def escape(str: str) -> str:
    """
    Takes any string and returns the escaped version to use in html.

    Parameters:
        str (str): The  string containing <, > etc.

    Returns:
        str: Escaped version of the input.
    """
    return str.replace(
        "&",
        "&amp;").replace(
        "<",
        "&lt;").replace(
            ">",
            "&gt;").replace(
                '\"',
                "&quot;").replace(
                    "'",
        "&apos;")


def read_file(file_path: str) -> str:
    """
    Reads and returns the content of a file.

    If file does not exist return empty string.

    Parameters:
        file_path (str): The path to the file to be read.

    Returns:
        str: The content of the file.
    """
    try:
        data = open(file_path, "r", encoding="utf-8").read()
    except BaseException:
        data = ""
    return data


def remove_date_time_parts(index_log: str) -> str:
    """
    Remove date and time from index log.
    ex. 2023-12-20 14:02:33.089	- INFO:  You specified the input format: TTL
    to: INFO:  You specified the input format: TTL

    Parameters:
        index_log (str): The index log.

    Returns:
        The index log without time and date as a string.
    """
    pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s*-"
    return re.sub(pattern, "", index_log)
