import os
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("search_log.log"),
        logging.StreamHandler()
    ]
)

def find_matching_json_files(root_dir, search_string='"key": "dataddo_extraction_timestamp"'):
    matching_files = []

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith(".json"):
                file_path = os.path.join(dirpath, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if search_string in content:
                            logging.info(f"Match found: {file_path}")
                            matching_files.append(file_path)
                except Exception as e:
                    logging.error(f"Error reading {file_path}: {e}")

    return matching_files


def main():
    '''
    Run from terminal:
    python find_json_files.py --root "C:\\Users\\tomne\\Dataddo\\api-php\\templates\\connector"
    '''
    parser = argparse.ArgumentParser(description="Search JSON files for a specific key.")
    parser.add_argument("--root", required=True, help="Root directory to search.")
    parser.add_argument(
        "--search",
        default='"key": "dataddo_extraction_timestamp"',
        #default='"dataddo_insert_date"',
        help="String to search inside JSON files."
    )
    args = parser.parse_args()

    logging.info(f"Searching in: {args.root}")
    results = find_matching_json_files(args.root, args.search)

    logging.info(f"Total matches: {len(results)}")


if __name__ == "__main__":
    main()
