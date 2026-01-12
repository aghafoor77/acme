import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime

from ACME import ACME
from JSONHandler import JSONHandler


def cmd_gt(args):
    print("=============================================================== 1")
    print(
        f"[GT] File: {args.file} | Vul File: {args.vul} | output Directory {args.output}"
    )

    if not os.path.isfile(args.file):
        print("❌  No input OpenAPI file exists !")
        return

    if not os.path.isfile(args.vul):
        print("❌ No input Vulernability file exists !")
        return

    if not os.path.isdir(args.output):
        print(f"❌ Not a output directory or does not exist: {args.file} !")
        return

    jsonh = JSONHandler()
    jObjStr = jsonh.read_string(args.vul)
    print(jObjStr)
    jObj = json.loads(jObjStr)
    print(jObj)
    head_prompt = {}
    for value in jObj:
        if value["isconsider"] is True:
            head_prompt[value["id"]] = value["vulnerability"]

    uuid_value = str(uuid.uuid4())
    print(uuid_value)
    output_dir = f"{args.output}{uuid_value}/"
    os.makedirs(output_dir, exist_ok=True)
    acme = ACME(args.output)
    acme.acmeEntry(uuid_value, args.file, output_dir, head_prompt)


def cmd_run(args):
    print("=============================================================== 2")
    print(
        f"[RUN] Testcase: {args.testcase} | Attributes: {args.attributes} | Output: {args.output}"
    )


def cmd_reinit(args):
    print("=============================================================== 3")
    print("[REINIT] Reinitializing resources...")


def cmd_exit(args):
    print("=============================================================== 4")
    print("[EXIT] Exiting CLI...")
    sys.exit(0)


def build_cli():
    parser = argparse.ArgumentParser(
        prog="acme-cli",
        description="ACME CLI Tool for GT, Run, Reinit and Exit commands",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- GT COMMAND ---
    gt_parser = subparsers.add_parser("gt", help="Generate GT using files")
    gt_parser.add_argument("-f", "--file", required=True, help="Input file")
    gt_parser.add_argument("-v", "--vul", required=True, help="Vulnerability file")
    gt_parser.add_argument(
        "-o", "--output", required=True, help="Output Testcases file"
    )
    gt_parser.set_defaults(func=cmd_gt)

    # --- RUN COMMAND ---
    run_parser = subparsers.add_parser("run", help="Run test with attributes")
    run_parser.add_argument("-t", "--testcase", required=True, help="Test case file")
    run_parser.add_argument(
        "-a", "--attributes", required=True, help="Attributes JSON file"
    )
    run_parser.add_argument("-o", "--output", required=True, help="Output report file")
    run_parser.set_defaults(func=cmd_run)

    # --- REINIT COMMAND ---
    reinit_parser = subparsers.add_parser("reinit", help="Reinitialize the system")
    reinit_parser.set_defaults(func=cmd_reinit)

    # --- EXIT COMMAND ---
    exit_parser = subparsers.add_parser("exit", help="Exit the program")
    exit_parser.set_defaults(func=cmd_exit)

    return parser


def display_warning_message(fp):
    warning_message = """
⚠️  WARNING! ⚠️
==============

Please specify values for all **environment variables**.  

⚡ Important notes:
  1. Carefully provide the values so that the output file is a **valid JSON**.
  2. Test results highly depend on the values provided.
  3. Make sure the values correspond to the **suggested names** of the variables.
  4. If environment variable is a JWT h=then please spcify a complete header value! 

Proceed carefully to avoid errors!
"""
    print(warning_message)
    print("==========================================")


def create_postman_environment_file(env_name, unique_list):
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


# Example usage
# variables = {
#   "base_url": "http://localhost:3000",
#  "auth_token": "Bearer abcdef123456",
# "user_email": "user@example.com"
# }

# create_postman_environment_file("MyEnvironment", variables, "environment_file.json")


def ret_env(jObj, fileDir):
    item = jObj["item"]
    vList = []
    for aVar in item:
        envRec = extract_postman_variables(json.dumps(aVar))
        if len(envRec) != 0:
            vList.extend(envRec)
    unique_list = list(set(vList))

    allVarVal = create_postman_environment_file(
        "ACME Environment variables", unique_list
    )

    file_path = f"{fileDir}environment_variables.json"

    if os.path.exists(file_path):
        print("⚠️ File already exists with environment_variables.json.")
        print(
            "If you press Y, the existing file will be overwritten, and any environment variables (if already set) will be deleted!"
        )
        name = input("Do you want to overwrite (Y/N)? ").strip().lower()
        if name in ["y", "yes"]:
            # your overwrite logic here
            with open(file_path, "w") as f:
                json.dump(allVarVal, f, indent=4)
            print(f"Environment variables file saved at '{file_path}'")
            display_warning_message(file_path)

        elif name in ["n", "no"]:
            name = input("Please enter file name :").strip().lower()
            file_path = f"{fileDir}{name}.json"
            with open(file_path, "w") as f:
                json.dump(allVarVal, f, indent=4)
            print(f"Environment variables file saved at '{file_path}'")
            display_warning_message(file_path)

        else:
            print("⚠️ Invalid input! Please enter Y or N.")
    else:
        print("❌ File does not exist.")


def extract_postman_variables(s):
    """
    Extracts all Postman-style variables from a string (e.g., {{user_id}}, {{token}})
    Returns a list of variable names without the curly braces.
    """

    pattern = r"\{\{([^}]+)\}\}"
    return list(set(re.findall(pattern, s)))  # set() removes duplicates


# Example:
# print(extract_postman_variables("Hello {{user_email}}, your token is {{access_token}} and again {{user_email}}"))
# Output: ['user_email', 'access_token']
def main():
    f = "/home/chaincode/Desktop/acmeimp/microsecai/input/post-postman.json"
    jsonh = JSONHandler()
    jObjStr = jsonh.read_string(f)
    jObj = json.loads(jObjStr)

    out = "/home/chaincode/Desktop/acmeimp/microsecai/result/"

    ret_env(jObj, out)

    parser = build_cli()

    while True:
        try:
            user_input = input("acme> ").strip()
            if not user_input:
                continue

            args = parser.parse_args(user_input.split())
            args.func(args)

        except SystemExit:
            # argparse throws SystemExit, ignore for loop continuation
            continue
        except KeyboardInterrupt:
            print("\n[EXIT] Interrupted by user")
            break


if __name__ == "__main__":
    main()
