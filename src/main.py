import sys
import json
from pathlib import Path
from cli_utils import install_requirements, read_url_file


# -----------------------------------------------------------------------------------
# IMPORTANT NOTE: ALL PRINT STATEMENTS NEED TO GO TO LOGFILE BASED ON VERBOSITY LEVEL
# -----------------------------------------------------------------------------------


def usage():
    print("Inorrect Usage -> Try: ./run <install|test|url_file>", file=sys.stderr)
    sys.exit(1)

def main():
    if len(sys.argv) != 2:
        usage()

    arg: str = sys.argv[1]

    if arg == "install":
        repo_root = Path(__file__).parent.parent.resolve()
        req_file = repo_root / "requirements.txt"
        exit_code = install_requirements(req_file)
        sys.exit(exit_code)

    elif arg == "test":
        #run all our tests here 
        sys.exit(0)

    else:
        try:
            model_info = read_url_file(arg)
        except FileNotFoundError:
            print(f"Error: File not found - {arg}", file=sys.stderr)
            sys.exit(1)

        for url in model_info:
            #We have to put the metrics here after we are able to properly calculate them
            result = {
                "URL": url,
                "NET_SCORE": 0.75,
                "RAMP_UP_SCORE": 0.60,
                "CORRECTNESS_SCORE": 0.80,
                "BUS_FACTOR_SCORE": 0.70,
                "RESPONSIVE_MAINTAINER_SCORE": 0.90,
                "LICENSE_SCORE": 1.00,
                "GOOD_PINNING_PRACTICE_SCORE": 0.50,
                "LATENCY": 123

            }
            print(json.dumps(result))
            

if __name__ == "__main__":
    main()