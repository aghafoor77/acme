import json
import os
import re


class FixerJSON:
    """
    A professional class for handling JSON data.

    Responsibilities:
    - Validate JSON strings
    - Save JSON to file
    - Append JSON entries to existing JSON arrays
    """

    def __init__(self):
        """
        Initialize FixerJSON.

        :param file_path: Path to the JSON file to save/load data
        """

    def validate_json_string(self, json_string: str):
        """
        Validate that a string is proper JSON.

        :param json_string: Input string
        :return: Python object if valid JSON
        :raises ValueError: If the string is invalid JSON
        """
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}")

    def save_json(self, data):
        """
        Save a Python object (dict or list) as JSON to file, overwriting existing content.

        :param data: Python dict or list
        """
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"✅ JSON data saved to {self.file_path}")

    def save_string(self, file_path: str, content: str):
        """
        Save a string to a file.

        :param content: String to save
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ String successfully saved to {file_path}")

    def read_string(self, file) -> str:
        """
        Read the content of the file and return it as a string.

        :return: File content as string
        """
        if not os.path.exists(file):
            raise FileNotFoundError(f"File not found: {file}")

        with open(file, "r", encoding="utf-8") as f:
            content = f.read()

        print(f"✅ String successfully read from {file}")
        return content

    def eliminate_repeat(self, json_str):
        exist = '\\"" + "A".repeat(10000) + "\\"'
        long_message = "A" * 10000
        replace = f'\\"{long_message}\\"'

        new_json_str = ""
        if ".repeat(" in json_str:
            match = re.search(r"\d+", json_str)

            if match:
                number = int(match.group())
                print(number)  # Output: 10000

            new_json_str = json_str.replace(exist, replace)
            print("Repeat found and replaced with lon message !")
        else:
            new_json_str = json_str
            print("Not found, no replacement")
            # Replace the big string with the compact one
            new_json_str = json_str.replace(exist, replace)

        return new_json_str


# Example usage
if __name__ == "__main__":
    fixerJSON = FixerJSON()

    contents = fixerJSON.read_string(
        "/home/chaincode/Desktop/acmeimp/microsecai/output/repeat.json"
    )
    new_json_str = fixerJSON.eliminate_repeat(contents)
    fixerJSON.validate_json_string(new_json_str)
    fixerJSON.save_string(
        "/home/chaincode/Desktop/acmeimp/microsecai/output/replaced.json", new_json_str
    )
