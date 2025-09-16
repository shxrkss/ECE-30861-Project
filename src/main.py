import sys
import json
from cli import *

def main():
    if len(sys.argv) != 2:
        #print("Usage: python cli.py <absolute_path_to_url_file>", file=sys.stderr)
        print("Usage: ./run <install|test|url_file>", file=sys.stderr)
        sys.exit(1)

    file_path: str = sys.argv[1]

    if file_path == "install":
        # this should be where all dependencies are installed
        sys.exit(0)
    elif file_path == "test":
        #run all our tests here 
        sys.exit(0)
    else:
        
        try:
            model_info = read_url_file(file_path)
        except FileNotFoundError:
            print(f"Error: File not found - {file_path}", file=sys.stderr)
            sys.exit(1)

        #for model_link, code_link, dataset_link in model_info:
            #print(f"{model_link}, {code_link if code_link else 'None'}, {dataset_link if dataset_link else 'None'}")
        for url in model_info:
            #We have to put the metrics here after we are able to properly calculate them
            result = {
                "URL": url,
                "NET_SCORE": 75,
                "RAMP_UP_SCORE": 60,
                "CORRECTNESS_SCORE": 80,
                "BUS_FACTOR_SCORE": 70,
                "RESPONSIVE_MAINTAINER_SCORE": 90,
                "LICENSE_SCORE": 100,
                "GOOD_PINNING_PRACTICE_SCORE": 50,
                "LATENCY": 123

            }
            print(json.dumps(result))
            

if __name__ == "__main__":
    main()