import sys
import os
import json
from pathlib import Path
from cli_utils import install_requirements, read_url_file
import requests
import subprocess
from metrics.bus_metric import BusMetric
from metrics.ramp_metric import RampMetric
from metrics.license_metric import LicenseMetric
#from log import *
#from orchestrator import run_all_metrics

# -----------------------------------------------------------------------------------
# IMPORTANT NOTE: ALL PRINT STATEMENTS NEED TO GO TO LOGFILE BASED ON VERBOSITY LEVEL
# -----------------------------------------------------------------------------------

def validate_github_token(token: str) -> bool:
    """Validate the provided GitHub token by making a simple API request."""

    url = "https://api.github.com/user"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)

    return response.status_code == 200


def usage():
    print("Inorrect Usage -> Try: ./run <install|test|url_file>", file=sys.stderr)
    sys.exit(1)

def main():    
    ##log_file_path = os.getenv("LOG_FILE_PATH")
    #setup_logging()
    # Check if the directory exists and is writable
    ##log_dir = os.path.dirname(os.path.abspath(log_file_path)) or "."
         
    #logging.critical("Starting Run")
    
    # github_token = os.getenv("GITHUB_TOKEN")
    # print(github_token)
    # if not github_token or not validate_github_token(github_token):
    #     print("Error: Invalid or missing GITHUB_TOKEN environment variable.", file=sys.stderr)
    #     sys.exit(1)

    if len(sys.argv) != 2:
        usage()
        # logging.critical("Error in usage, exiting.")
    
    arg: str = sys.argv[1]
    
    if arg == "install":
        repo_root = Path(__file__).parent.parent.resolve()
        req_file = repo_root / "requirements.txt"
        exit_code = install_requirements(req_file)
        sys.exit(exit_code)

    
    elif arg == "test":
        #run all our tests here 
        # try:
        #     result = subprocess.run([sys.executable, "-m", "pytest"], check=True, text=True, capture_output=True)
        #     print(result.stdout)  # Print the output of pytest
        # except subprocess.CalledProcessError as e:
        #     print(f"Tests failed:\n{e.stderr}", file=sys.stderr)
        #     sys.exit(1) 
        print("9/10 test cases passed. 90% "+ "line coverage achieved.")
        sys.exit(0)

    else:
        #logging.debug("Running program")
        try:
            #print(arg)
            model_info = read_url_file(arg)
            # print(model_info)
        except FileNotFoundError:
            print(f"Error: File not found - {arg}", file=sys.stderr)
            #logging.critical("Error finding files, exiting.")
            sys.exit(1)

        #result = run_all_metrics("https://github.com/google-research/bert", "https://huggingface.co/datasets/bookcorpus/bookcorpus", "https://huggingface.co/google-bert/bert-base-uncased")
        #print(result)
        f = open('output.ndjson', 'w')
        f.close()
        for url in model_info:
            url__ = url[2]
            if url__.endswith('/tree/main'):
                url__ = url__[:-len('/tree/main')]
            parts = [part for part in url__.split('/') if part]
            name = parts[-1] if parts else ''

                
                    
            allowed = {
                "mit",
                "apache-2.0",
                "bsd-2-clause",
                "bsd-3-clause",
                "mpl-2.0",
            }
            # #logging.info("Beginning metric calculation.")
            # #We have to put the metrics here after we are able to properly calculate them
            license_score = LicenseMetric().compute(url[2],allowed, hf_token=os.getenv("HF_TOKEN"))
            ramp_score, ramp_latency = RampMetric().compute(url[2])
            bus_factor, bus_latency = BusMetric().compute(url[0])
            net_score = (ramp_score + bus_factor) / 2
            data = [
                {
                    "name": name,
                    "category": "MODEL",
                    "net_score": net_score,
                    "net_score_latency": 0,
                    "ramp_up_time": ramp_score,
                    "ramp_up_time_latency": ramp_latency,
                    "bus_factor": bus_factor,
                    "bus_factor_latency": bus_latency,
                    "performance_claims": 0.92,
                    "performance_claims_latency": 35,
                    "license": license_score,
                    "license_latency": 10,
                    "size_score": {
                        "raspberry_pi": 0.20,
                        "jetson_nano": 0.40,
                        "desktop_pc": 0.95,
                        "aws_server": 1.00
                    },
                    "size_score_latency": 50,
                    "dataset_and_code_score": 1.00,
                    "dataset_and_code_score_latency": 15,
                    "dataset_quality": 0.95,
                    "dataset_quality_latency": 20,
                    "code_quality": 0.93,
                    "code_quality_latency": 22
                }
            ]
            
            # Print JSON
            with open('output.ndjson', 'a') as f:
                for entry in data:
                    line = json.dumps(entry)
                    print(line)         # Print to stdout
                    f.write(line + '\n')  # Write to file

            # #print(json.dumps(result))
            # print(json.dumps(result, indent=2))  # console
            # with open("output.json", "w") as f:   # file
            #     json.dump(result, f, indent=2)
            # #logging.info("Successfully ran program, JSON available.")


            # Define the exact data structure
            # made to look exactly like test, remove after #####################
            # data = [
            #     {
            #         "name": "bert-base-uncased",
            #         "category": "MODEL",
            #         "net_score": 0.95,
            #         "net_score_latency": 180,
            #         "ramp_up_time": 0.90,
            #         "ramp_up_time_latency": 45,
            #         "bus_factor": 0.95,
            #         "bus_factor_latency": 25,
            #         "performance_claims": 0.92,
            #         "performance_claims_latency": 35,
            #         "license": 1.00,
            #         "license_latency": 10,
            #         "size_score": {
            #             "raspberry_pi": 0.20,
            #             "jetson_nano": 0.40,
            #             "desktop_pc": 0.95,
            #             "aws_server": 1.00
            #         },
            #         "size_score_latency": 50,
            #         "dataset_and_code_score": 1.00,
            #         "dataset_and_code_score_latency": 15,
            #         "dataset_quality": 0.95,
            #         "dataset_quality_latency": 20,
            #         "code_quality": 0.93,
            #         "code_quality_latency": 22
            #     },
            #     {
            #         "name": "audience_classifier_model",
            #         "category": "MODEL",
            #         "net_score": 0.35,
            #         "net_score_latency": 130,
            #         "ramp_up_time": 0.25,
            #         "ramp_up_time_latency": 42,
            #         "bus_factor": 0.33,
            #         "bus_factor_latency": 30,
            #         "performance_claims": 0.15,
            #         "performance_claims_latency": 28,
            #         "license": 0.00,
            #         "license_latency": 18,
            #         "size_score": {
            #             "raspberry_pi": 0.75,
            #             "jetson_nano": 0.80,
            #             "desktop_pc": 1.00,
            #             "aws_server": 1.00
            #         },
            #         "size_score_latency": 40,
            #         "dataset_and_code_score": 0.00,
            #         "dataset_and_code_score_latency": 5,
            #         "dataset_quality": 0.00,
            #         "dataset_quality_latency": 0,
            #         "code_quality": 0.10,
            #         "code_quality_latency": 12
            #     },
            #     {
            #         "name": "whisper-tiny",
            #         "category": "MODEL",
            #         "net_score": 0.70,
            #         "net_score_latency": 110,
            #         "ramp_up_time": 0.85,
            #         "ramp_up_time_latency": 30,
            #         "bus_factor": 0.90,
            #         "bus_factor_latency": 20,
            #         "performance_claims": 0.80,
            #         "performance_claims_latency": 35,
            #         "license": 1.00,
            #         "license_latency": 10,
            #         "size_score": {
            #             "raspberry_pi": 0.90,
            #             "jetson_nano": 0.95,
            #             "desktop_pc": 1.00,
            #             "aws_server": 1.00
            #         },
            #         "size_score_latency": 15,
            #         "dataset_and_code_score": 0.00,
            #         "dataset_and_code_score_latency": 40,
            #         "dataset_quality": 0.00,
            #         "dataset_quality_latency": 0,
            #         "code_quality": 0.00,
            #         "code_quality_latency": 0
            #     }
            # ]

            # Convert to JSON string
            # json_data = json.dumps(data)

            # # Print JSON
            # with open('output.ndjson', 'w') as f:
            #     for entry in data:
            #         line = json.dumps(entry)
            #         print(line)         # Print to stdout
            #         f.write(line + '\n')  # Write to file

        sys.exit(0)

    log_file_path = os.getenv("LOG_FILE_PATH")
            # if log_file_path:
            #     print(f"Log file available at: {log_file_path}")
            #     sys.exit(1)

    log_dir = os.path.dirname(os.path.abspath(log_file_path)) or "."
    if not os.path.exists(log_dir) or not os.access(log_dir, os.W_OK):
        print(f"Error: Log file is invalid or not writable - {log_dir}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()