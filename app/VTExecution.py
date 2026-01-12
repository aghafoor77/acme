import json
import subprocess
from pathlib import Path


class NewmanRunner:
    def __init__(
        self, collection_path, environment_path=None, report_dir=None, reporters=None
    ):
        """
        Initialize the NewmanRunner class.

        Args:
            collection_path (str or Path): Path to the Postman collection JSON file.
            environment_path (str or Path, optional): Path to Postman environment JSON file.
            report_dir (str or Path, optional): Directory to store JSON report (default: same as collection file).
            reporters (list, optional): List of Newman reporters to use (default: ["cli", "json"]).
        """
        self.collection_path = Path(collection_path)
        if not self.collection_path.is_file():
            raise FileNotFoundError(
                f"Collection file not found: {self.collection_path}"
            )

        self.environment_path = Path(environment_path) if environment_path else None
        if self.environment_path and not self.environment_path.is_file():
            raise FileNotFoundError(
                f"Environment file not found: {self.environment_path}"
            )

        self.report_dir = (
            Path(report_dir) if report_dir else self.collection_path.parent
        )
        self.report_dir.mkdir(parents=True, exist_ok=True)

        self.reporters = reporters or ["cli", "json"]
        self.report_file = self.report_dir / "newman_report.json"
        self.result_json = None

    def run_collection(self):
        """Run the Newman collection and save the JSON report."""
        command = ["newman", "run", str(self.collection_path)]
        if self.environment_path:
            command += ["-e", str(self.environment_path)]
        command += [
            "--reporters",
            ",".join(self.reporters),
            "--reporter-json-export",
            str(self.report_file),
        ]

        try:
            print(f"Running Newman collection: {self.collection_path.name}")

            print(f"{command}")
            subprocess.run(command, check=True)

            if self.report_file.is_file():
                with open(self.report_file, "r") as f:
                    self.result_json = json.load(f)
            else:
                raise RuntimeError("Newman did not generate a JSON report.")
        except Exception as e:
            print(
                "Error: Seems Newman is not installed, please install first and then try !"
            )
            raise RuntimeError(f"Newman execution failed: {e}")

    def summarize_results(self):
        """
        Summarize the Newman JSON results.

        Returns:
            dict: Summary with counts of total, passed, failed, skipped requests.
        """
        if not self.result_json:
            raise RuntimeError(
                "No results found. Please run the collection first using run_collection()."
            )

        summary = {
            "total_requests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "failed_requests": [],
        }

        run = self.result_json.get("run", {})
        executions = run.get("executions", [])

        for exec_ in executions:
            summary["total_requests"] += 1
            assertion_results = exec_.get("assertions", [])
            if not assertion_results:
                summary["skipped"] += 1
                continue

            failed = any(a.get("error") for a in assertion_results)
            if failed:
                summary["failed"] += 1
                summary["failed_requests"].append(
                    {
                        "name": exec_.get("item", {}).get("name"),
                        "request": exec_.get("request", {}).get("url", {}).get("raw"),
                        "errors": [
                            a.get("error") for a in assertion_results if a.get("error")
                        ],
                    }
                )
            else:
                summary["passed"] += 1

        return summary

    def print_summary(self):
        """Print a nicely formatted summary to console."""
        summary = self.summarize_results()
        print("===== Newman Test Summary =====")
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Skipped: {summary['skipped']}")
        if summary["failed_requests"]:
            print("\nFailed Requests Details:")
            for f in summary["failed_requests"]:
                print(f"- {f['name']} | URL: {f['request']}")
                for err in f["errors"]:
                    print(f"   Error: {err['message']}")


# Example usage
if __name__ == "__main__":
    collection_file = "/home/chaincode/Desktop/acmeimp/tests/updated/post-postman.json"
    environment_file = "/home/chaincode/Desktop/acmeimp/tests/updated/environment_variables.json"  # optional

    runner = NewmanRunner(collection_file, environment_file)
    runner.run_collection()
    runner.print_summary()
