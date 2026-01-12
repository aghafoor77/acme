import ast
import json
import logging
import os
import re

# ==================== Logging Setup ====================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(filename)s:%(lineno)d] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler("acme.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
# =======================================================


class JSONHandler:
    start_pattern = "***_-START_ACME_SCRIPT_HERE-_***"
    end_pattern = "***_-END_ACME_SCRIPT_HERE-_***"
    """
    A professional class for handling JSON data.
    
    Responsibilities:
    - Validate JSON strings
    - Save JSON to file
    - Append JSON entries to existing JSON arrays
    """

    def __init__(self):
        """
        Initialize JSONHandler.

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
            logger.error(f"Invalid JSON string: {e}")
            raise ValueError(f"Invalid JSON string: {e}")

    def save_json(self, data):
        """
        Save a Python object (dict or list) as JSON to file, overwriting existing content.

        :param data: Python dict or list
        """
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        logger.info(f"✅ JSON data saved to {self.file_path}")

    def append_json(self, json_string: str):
        """
        Append a JSON string as a new entry to a JSON array in the file.

        :param json_string: JSON string to append
        :raises ValueError: If input string is invalid JSON
        """
        new_entry = self.validate_json_string(json_string)

        # Load existing file or initialize as empty array
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        logger.error("Existing JSON file is not a list. Cannot append.")
                        raise ValueError(
                            "Existing JSON file is not a list. Cannot append."
                        )
            except json.JSONDecodeError:
                logger.error("Existing JSON file is invalid.")
                raise ValueError("Existing JSON file is invalid.")
        else:
            existing_data = []

        existing_data.append(new_entry)

        # Save updated array back to file
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4)

        logger.info(f"✅ JSON entry appended to {self.file_path}")

    def save_string(self, file_path: str, content: str):
        """
        Save a string to a file.

        :param content: String to save
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"✅ String successfully saved to {file_path}")

    def build_postman_script(self, var_dict):
        """
        Build a Postman pre-request script JSON string, where each key in var_dict
        is a variable name and its value is the length for generateLargeRandomString(length).

        Example:
            var_dict = {"tokenA": 10, "tokenB": 25}
        """

        # Shared JavaScript function to generate random strings
        script_lines = [
            "function generateLargeRandomString(length) {",
            "    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';",
            "    const charactersLength = characters.length;",
            "    const chunkSize = 10000; // generate 10k chars at a time",
            "    let result = [];",
            "",
            "    let remaining = length;",
            "    while (remaining > 0) {",
            "        const currentChunkSize = Math.min(chunkSize, remaining);",
            "        const chunk = new Array(currentChunkSize);",
            "",
            "        for (let i = 0; i < currentChunkSize; i++) {",
            "            chunk[i] = characters[Math.floor(Math.random() * charactersLength)];",
            "        }",
            "",
            "        result.push(chunk.join(''));",
            "        remaining -= currentChunkSize;",
            "    }",
            "",
            "    return result.join('');",
            "}",
            "",
        ]

        # Add JavaScript for each variable/length pair
        for var_name, length in var_dict.items():
            script_lines.extend(
                [
                    f"{var_name} = generateLargeRandomString({length});",
                    f"pm.environment.set('{var_name}', {var_name});",
                    "",
                ]
            )

        # Wrap in Postman-style JSON structure
        postman_data = [
            {
                "listen": "prerequest",
                "script": {
                    "exec": script_lines,
                    "type": "text/javascript",
                    "packages": {},
                    "requests": {},
                },
            }
        ]

        # Return formatted JSON string
        return postman_data

    def read_string(self, file) -> str:
        """
        Read the content of the file and return it as a string.

        :return: File content as string
        """
        if not os.path.exists(file):
            raise FileNotFoundError(f"File not found: {file}")

        with open(file, "r", encoding="utf-8") as f:
            content = f.read()

        logger.info(f"✅ String successfully read from {file}")
        return content

    def extract_postman_items(self, postman):
        index = postman.find('"item"')
        result = ""
        if index != -1:
            # Extract everything after the found substring
            result = postman[index + len('"item"') :].strip()
            # print(result)
        else:
            print("")
        # Remove  :

        index = result.find(":")
        if index != -1:
            # Extract everything after the found substring
            result = result[index + len(":") :].strip()
            # print(result)
        else:
            print("")
        # Remove [
        index = result.find("[")
        if index != -1:
            # Extract everything after the found substring
            result = result[index + len("[") + 1 :].strip()
            # print(result)
        else:
            print("")

        index = result.rfind("]")
        if index != -1:
            # Keep everything up to and including the last ']'
            result = result[:index]
        else:
            print("")
        return result

    def find_chars_to_replace(self, big, start, end):
        new_start = 0
        new_end = 0
        i = 0
        start = start - 1
        while True:
            ch = big[start - i]
            if ch == ",":
                i = i + 1
                new_start = start - i
                break
            if ch == '"':
                i = i + 1
                new_start = start - i + 1
                break
            if ch == "[" or ch == "{":
                i = i + 1
                new_start = start - i + 1
                break

            i = i + 1
        i = 0
        while True:
            ch = big[end + i]
            if ch == '"':
                i = i + 1
                new_end = end + i
                # print(big[new_start:new_end].lstrip())
                break
            if ch == ",":
                i = i + 1
                new_end = end + i
                break
            if ch == "]" or ch == "}":
                i = i + 1
                new_end = end + i
                break
            i = i + 1

        if new_start < new_end:
            return big[new_start:new_end].lstrip()
        else:
            """"""
        # print(big[new_start:new_end])

    def to_replace_with(self, input):
        localpattern = re.compile(pattern=r'"([^"]*)"\.repeat\((\d+)\)')
        matches = localpattern.findall(input)
        for chars, num in matches:
            # long_message = chars * int(num)
            # Here to add script realted stuff
            replace = f"{JSONHandler.start_pattern}{num}{JSONHandler.end_pattern}"  # Add pattern and then replace with java script functions f'{long_message}'
            if input[0] == '"' and input[len(input) - 1] == ",":
                return f'{replace}",'

            if input[0] == '"' and input[len(input) - 1] == '"':
                return replace

    def eliminate_repeat(self, big):
        pattern = re.compile(r'"[^"]*"\.repeat\(\d+\)')
        matches = list(pattern.finditer(big))
        json_str = big

        for i, m in enumerate(matches, 1):
            start, end = m.span()
            match = m.group()
            localpattern = re.compile(r'"([^"]*)"\.repeat\((\d+)\)')
            matches = localpattern.findall(match)

            for chars, num in matches:
                exist = self.find_chars_to_replace(big, start, end)
                if exist != "":
                    replace = self.to_replace_with(exist)
                    json_str = json_str.replace(exist, replace)

        return json_str

    def find_index_of_plus(self, str, start, end):
        new_start = 0
        new_end = 0
        i = 0
        if str[start] != '"':
            start = start - 1
            while True:
                ch = str[start - i]
                if ch == '"':
                    i = i + 1
                    new_start = start - i
                    break
        else:
            new_start = start
        i = 0
        while True:
            ch = str[end + i]
            if ch == '"':
                i = i + 1
                new_end = end + i
                break

            i = i + 1
        if new_start < new_end:
            return str[new_start:new_end].lstrip()
        else:
            """"""

    def fix_json_string(self, raw_str: str):
        # Step 1: Remove outer quotes if present
        if raw_str.startswith('"') and raw_str.endswith('"'):
            raw_str = raw_str[1:-1]

            # Step 2: Replace improperly escaped quotes with normal quotes
            raw_str = raw_str.replace('\\"', '"')

            # Step 3: Remove stray quotes between key-value pairs
            raw_str = re.sub(r'"?,\s*"', ",", raw_str)

            # Step 4: Remove trailing commas before closing braces
            raw_str = re.sub(r",\s*([}])", r"\1", raw_str)

            # Step 5: Attempt to parse
        try:
            # print(raw_str)
            return json.loads(raw_str)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Parsing failed: {e}, trying literal_eval ")
            # As last resort, try using ast.literal_eval

            try:
                return ast.literal_eval(raw_str)
            except Exception as e2:
                logger.error(f"❌ Literal eval failed:: {e2}")
                return None

    def rescue_parse_list(self, raw_string: str):
        # Pattern to find "raw": "..."
        pattern = r'"raw"\s*:\s*"(.+?)"(?=,|\s*\})'

        matches = re.finditer(pattern, raw_string, re.DOTALL)

        fixed_text = raw_string
        for match in matches:
            raw_content = match.group(1)

            # Remove stray characters after the last valid quote
            last_quote_index = raw_content.rfind('"')
            if last_quote_index != -1:
                raw_content = raw_content[: last_quote_index + 1]

            # Remove newlines and escape inner quotes
            raw_content = raw_content.replace("\n", "").replace('"', '\\"')

            # Replace original content with fixed content
            fixed_text = fixed_text.replace(match.group(0), f'"raw": "{raw_content}"')
        try:
            json_data = json.loads(fixed_text)
            logger.info("✅ JSON loaded successfully !")
            return json_data
        except json.JSONDecodeError as e:
            print("JSON is still invalid:", e)
            return []

    def rescue_parse_raw_(self, raw_str):
        # Remove outer quotes
        if raw_str.startswith('"') and raw_str.endswith('"'):
            raw_str = raw_str[1:-1]

        # Replace escaped quotes with actual quotes
        raw_str = raw_str.replace('\\"', '"')

        # Split on comma followed by a quote and key (heuristic)
        # This is a safe split for malformed raw JSON like your example
        parts = re.split(r',\s*(?="?\w+"\s*:)', raw_str)

        clean_dict = {}
        for part in parts:
            # Remove any stray quotes at start/end
            part = part.strip('", ')
            if not part:
                continue

            # Split into key and value
            if ":" not in part:
                continue
            key, value = part.split(":", 1)
            key = key.strip().strip('"')
            value = value.strip().strip('"')

            clean_dict[key] = value

        return clean_dict

    def extract_json_objects(sefl, text):
        objects = []
        brace_level = 0
        start = None

        for i, ch in enumerate(text):
            if ch == "{":
                if brace_level == 0:
                    start = i
                brace_level += 1
            elif ch == "}":
                brace_level -= 1
                if brace_level == 0 and start is not None:
                    objects.append(text[start : i + 1])
                    start = None
        return objects

    # Step 2: Try parsing each object, collect good and bad ones
    def parse_item(self, data):
        objs = self.extract_json_objects(data)
        valid = []
        invalid = []
        result = []

        for idx, obj in enumerate(objs, 1):
            try:
                parsed = json.loads(obj)
                valid.append(parsed)
                logger.info(f"✅ Object #{idx} parsed successfully")
            except Exception as e:
                invalid.append({"index": idx, "error": str(e), "object": obj})
                logger.warn(f"❌ Warnning in object #{idx}: {e}")
        result.append(valid)
        result.append(invalid)

        # Step 3: Save results
        # with open("valid.json", "w", encoding="utf-8") as f:
        #   json.dump(valid, f, indent=2, ensure_ascii=False)

        # with open("invalid.json", "w", encoding="utf-8") as f:
        #   json.dump(invalid, f, indent=2, ensure_ascii=False)

        print("\nSummary:")
        logger.info(f"✅ {len(valid)} valid objects")
        logger.info(f"❌ {len(invalid)} invalid objects")
        return result


# Example usage
if __name__ == "__main__":
    jsonHandler = JSONHandler()
    file_path = "/home/chaincode/Desktop/acmeimp/microsecai/result/8aeef669-5da5-4848-81be-488187f6cb31/1.json"

    output = jsonHandler.read_string(file_path)

    allItems = jsonHandler.eliminate_repeat(output)
    print(allItems)
    # jsonHandler.parse_item(output)

    # clean_dict = jsonHandler.rescue_parse_raw_(output)
    # print(json.dumps(clean_dict, indent = 4))
    # jsonHandler.fix_json_string (output)
