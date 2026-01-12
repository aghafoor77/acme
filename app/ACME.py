import json
import logging
import re
import uuid
from datetime import datetime

from ACMEFuzzer import ACMEFuzzer
from AIEngine import AIEngine
from JSONHandler import JSONHandler
from OpenAPIHandler import OpenAPIHandler
from VTPrompts import VTPrompts

# ==================== Logging Setup ====================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(filename)s:%(lineno)d] [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler("acme.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
# =======================================================


class ACME:
    def __init__(self, output_dir_):
        self.jsonHandler = JSONHandler()
        self.output_dir = output_dir_
        logger.info(f"Initialized ACME with output_dir: {output_dir_}")

    def ai_vts(self, openapi_file, head_prompt):
        vtPrompts = VTPrompts()
        aiEngine = AIEngine()
        output = ""
        allvtpm_items = ""

        try:
            openAPIHandler = OpenAPIHandler(openapi_file)
            endpoints = openAPIHandler.get_endpoints()
            logger.info(
                f"Found {len(endpoints)} endpoints in OpenAPI file: {openapi_file}"
            )

            prompts = []
            client = aiEngine.create_ai_cient()

            for an_ep in endpoints:
                prompts.append(vtPrompts.create_prompt_for_postman(an_ep, head_prompt))

            for i, aprompt in enumerate(prompts):
                output = aiEngine.generate_with_llm(aprompt, client)
                if "{" in output and "}" in output:
                    output = output[output.find("{") : output.rfind("}") + 1]
                else:
                    logger.warning("Invalid Postman file format detected!")

                cleaned_items = self.jsonHandler.extract_postman_items(output)

                try:
                    file_path = f"{self.output_dir}{i}.json"
                    self.jsonHandler.save_string(file_path, cleaned_items)
                    logger.info(f"Saved cleaned items to {file_path}")

                    onlyitems = self.data_cleaner(cleaned_items, i)
                    if onlyitems:
                        allvtpm_items += onlyitems + ","

                except Exception:
                    logger.error(
                        "Error while processing individual endpoint", exc_info=True
                    )

            return allvtpm_items.rstrip(",")

        except Exception:
            logger.error("Error in ai_vts()", exc_info=True)
            return allvtpm_items.rstrip(",")

    def data_cleaner(self, input, i):
        allItems = self.jsonHandler.eliminate_repeat(input)
        pattern = r'"\s\+'
        matches = re.finditer(pattern, allItems)
        temp = allItems
        for match in matches:
            exist = self.jsonHandler.find_index_of_plus(
                allItems, match.start(), match.end()
            )
            temp = temp.replace(exist, "")

        try:
            json.loads("[" + temp + "]")
            return temp
        except Exception:
            logger.error(
                "Invalid JSON format in test cases. Attempting recovery...",
                exc_info=False,
            )
            result = self.jsonHandler.parse_item(temp)
            try:
                valid = result[0]
                return json.dumps(valid, indent=4)[1:-1]
            except Exception:
                if len(result[1]) > 0:
                    file_path = f"{self.output_dir}invalid_{i}.json"
                    self.jsonHandler.save_string(file_path, result[1])
                    logger.warning(f"Saved invalid items to {file_path}")
                logger.error("Could not fix or recover test cases")
                return ""

    def fuzz_vts(self, openapi_file):
        try:
            openAPIHandler = OpenAPIHandler(openapi_file)
            endpoints = openAPIHandler.get_endpoints()
            paths = {p["path"]: p["endpoint"] for p in endpoints}

            fuzzer = ACMEFuzzer()
            fuzzer_items = fuzzer.build_collection(paths)

            fuzz_str_items = json.dumps(fuzzer_items, indent=4)
            index = fuzz_str_items.find("[")
            if index != -1:
                fuzz_str_items = fuzz_str_items[index + 1 :].strip()

            index = fuzz_str_items.rindex("]")
            if index != -1:
                fuzz_str_items = fuzz_str_items[:index]

            logger.info("Fuzz test cases generated successfully")
            return fuzz_str_items

        except Exception:
            logger.error("Error in fuzz_vts()", exc_info=True)
            return ""

    def converto_to_postman(self, items, file_id):
        postman = (
            """{
            "info": {
            "name": "ACME generated vulnerability test cases !",
            "_postman_id": \""""
            + file_id
            + """\",
            "description": "***** Disclaimer for AI-Generated Test Cases *****\\n- These vulnerability test cases have been automatically generated by an AI model and are provided as-is.\\n- Users are strongly advised to carefully review and validate them before execution.\\n- The ACME team makes no warranties, express or implied, regarding the accuracy, completeness, or suitability of these test cases.\\n- The ACME team does not accept responsibility for any errors, damages, losses, or failure to meet legal or regulatory requirements arising from their use.\\n- By using these test cases, you acknowledge and agree that all risks and impacts of execution lie solely with you as the user.\\n- No legal claims, actions, or proceedings may be initiated against the ACME team in connection with any loss or damage resulting from the use of these test cases.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item":"""
            + items
            + "}"
        )
        return postman

    def extract_placeholders(self, text: str) -> list:
        """
        Extracts all placeholders of the form {{variable_name}} from the input string.

        Args:
            text (str): Input string to search.

        Returns:
            list: List of placeholder names without the curly braces.
        """
        # Regex pattern to match {{some_text}} where some_text can include letters, digits, underscores
        pattern = r"\{\{([a-zA-Z0-9_]+)\}\}"

        # Find all matches
        matches = re.findall(pattern, text)
        return matches

    def add_pre_request_event(self, item, no):
        str_item = json.dumps(item)
        pattern = rf"{re.escape(self.jsonHandler.start_pattern)}(\d+){re.escape(self.jsonHandler.end_pattern)}"
        matches = list(re.finditer(pattern, str_item))
        if len(matches) > 0:
            env_param = {}
            for i, match in enumerate(matches, start=1):
                env_param[f"avt{no}{i}"] = match.group(1)
                str_item = str_item.replace(match.group(0), f"{{{{avt{no}{i}}}}}", 1)
            event = self.jsonHandler.build_postman_script(env_param)
            updated_item = json.loads(str_item)
            updated_item["event"] = event
            return updated_item
        else:
            return item

    def tag_testcase(self, postman):
        try:
            jsonObj = json.loads(postman)
            items = jsonObj["item"]
            updated_items = []
            variable = []
            no = 1
            for i in items:
                if "name" in i:
                    i["name"] = f"VTC {no} - {i['name']}"
                    i = self.add_pre_request_event(i, no)
                    updated_items.append(i)
                    no += 1

                aVar = self.extract_placeholders(json.dumps(i))
                variable.extend(aVar)
            jsonObj["item"] = updated_items
            variable = list(set(variable))
            now_utc = datetime.utcnow()
            # Format as "YYYY-MM-DDTHH:MM:SS.mmmZ"
            formatted_date = now_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

            a_env = {}
            a_env["id"] = "env123"
            a_env["name"] = "ACME_Environment_Variables"
            a_env["_postman_variable_scope"] = "environment"
            a_env["_postman_exported_at"] = formatted_date
            a_env["_postman_exported_using"] = "Postman/10.0.0"

            values = []
            for e in variable:
                eval_dict = {}
                eval_dict["key"] = e
                eval_dict["value"] = f"Add_value_of_{e}"
                eval_dict["enabled"] = "true"
                values.append(eval_dict)
            a_env["values"] = values
            envList = []
            envList.append(a_env)
            jsonObj["environments"] = envList
            return json.dumps(jsonObj, separators=(",", ":"))

        except Exception as e:
            logger.error("Error in tag_testcase()", exc_info=True)

    def acmeEntry(self, file_id, openapi_file, output_dir, head_prompt):
        logger.info("Starting ACME test case generation process")
        acme = ACME(f"{output_dir}")
        jsonHandler = JSONHandler()
        # head_prompt_test = {"API1:2023": "Broken Object Level Authorization"}

        aiItems = acme.ai_vts(openapi_file, head_prompt)
        fuzzItems = acme.fuzz_vts(openapi_file)
        if aiItems.endswith(","):
            aiItems = aiItems[:-1]
        if fuzzItems.endswith(","):
            fuzzItems = fuzzItems[:-1]

        if aiItems != "":
            allItems = aiItems + "," + fuzzItems
        else:
            allItems = fuzzItems

        logger.info("Saving all combined items")
        file_path = f"{output_dir}allitems.json"
        jsonHandler.save_string(file_path, allItems)

        logger.info("Generating pre-postman output")
        file_path = f"{output_dir}pre-postman.json"
        postman = acme.converto_to_postman(f"[{allItems}]", file_id)
        jsonHandler.save_string(file_path, postman)

        logger.info("Generating post-postman output with tagged test cases")
        post_postman = acme.tag_testcase(postman)
        file_path = f"{output_dir}post-postman.json"
        jsonHandler.save_string(file_path, post_postman)

        jsonh = JSONHandler()
        jObjStr = jsonh.read_string(file_path)
        jObj = json.loads(jObjStr)
        acme.ret_env(jObj, output_dir)

        logger.info("ACME process completed successfully")

    # ---------------------------------------------------------
    def extract_postman_variables(self, s):
        """
        Extracts all Postman-style variables from a string (e.g., {{user_id}}, {{token}})
        Returns a list of variable names without the curly braces.
        """

        pattern = r"\{\{([^}]+)\}\}"
        return list(set(re.findall(pattern, s)))  # set() removes duplicates

    def create_postman_environment_file(self, env_name, unique_list):
        env_data = {
            "id": str(uuid.uuid4()),
            "name": env_name,
            "values": [],
            "_postman_variable_scope": "environment",
            "_postman_exported_at": datetime.utcnow().isoformat() + "Z",
            "_postman_exported_using": "Python Script",
        }

        for a in unique_list:
            env_data["values"].append({"key": a, "value": "", "enabled": True})
        return env_data

    def ret_env(self, jObj, fileDir):
        item = jObj["item"]
        vList = []
        unique_list = []
        for aVar in item:
            envRec = self.extract_postman_variables(json.dumps(aVar))
            if len(envRec) != 0:
                vList.extend(envRec)
                unique_list = list(set(vList))

        allVarVal = self.create_postman_environment_file(
            "ACME Environment variables", unique_list
        )

        file_path = f"{fileDir}environment_variables.json"

        # your overwrite logic here
        with open(file_path, "w") as f:
            json.dump(allVarVal, f, indent=4)
            print(f"Environment variables file saved at '{file_path}'")

    """def acmeScript(self, file_id,openapi_file, output_dir) :
        logger.info("Starting ACME test case generation process")
        acme = ACME(f"{output_dir}")
        jsonHandler = JSONHandler()

        head_prompt_test = {"API1:2023": "Broken Object Level Authorization"}

        
        ppp = "/home/chaincode/Desktop/acmeimp/microsecai/result/8aeef669-5da5-4848-81be-488187f6cb31/"
        aiItems = ""
        for i in range(7): 
            toclean = onlyitems = jsonHandler.read_string(f"{ppp}/{i}.json")
            print(i)
            onlyitems = self.data_cleaner(toclean , i)
            if onlyitems:
               aiItems += onlyitems + ","
            print("=============")
            #aiItems = acme.ai_vts(openapi_file, head_prompt_test)
        
        jsonHandler.save_string(f"{ppp}/all.json", aiItems)

        fuzzItems = acme.fuzz_vts(openapi_file)
        if aiItems.endswith(","):
            aiItems = aiItems[:-1] 
        if fuzzItems.endswith(","):
            fuzzItems = fuzzItems[:-1] 

        if aiItems != "":    
            allItems = aiItems + "," + fuzzItems
        else:
            allItems = fuzzItems
            
        logger.info("Saving all combined items")
        file_path = f"{output_dir}allitems.json"
        jsonHandler.save_string(file_path, allItems)

        logger.info("Generating pre-postman output")
        file_path = f"{output_dir}pre-postman.json"
        postman = acme.converto_to_postman(f'[{allItems}]', file_id)
        jsonHandler.save_string(file_path, postman)

        logger.info("Generating post-postman output with tagged test cases")
        post_postman = acme.tag_testcase(postman)
        file_path = f"{output_dir}post-postman.json"
        jsonHandler.save_string(file_path, post_postman)

        logger.info("ACME process completed successfully")"""


if __name__ == "__main__":
    output_dir = "/home/chaincode/Desktop/acmeimp/microsecai/result/bbc/"
    acme = ACME(output_dir)
    """uuid_value = str(uuid.uuid4())
    output_dir = f"/home/chaincode/Desktop/acmeimp/microsecai/result/bbc/"
    acme = ACME(output_dir)
    ppp = "/home/chaincode/Desktop/acmeimp/microsecai/input/medicalreport.yaml"
    head_prompt_test = {"API1:2023": "Broken Object Level Authorization"}
    acme.acmeEntry(uuid_value, ppp, output_dir, head_prompt_test)"""

    jsonHandler = JSONHandler()
    postman = jsonHandler.read_string(
        "/home/chaincode/Desktop/acmeimp/tets/pre-postman.json"
    )
    logger.info("Generating post-postman output with tagged test cases")
    post_postman = acme.tag_testcase(postman)
    print(post_postman)
