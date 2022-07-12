"""
To run this script type: 'python cli_print_test.py'
You must use python3 and have the pandas package installed.
"""

import re
import sys

from pathlib import Path
from datetime import datetime

from argparse import (
    ArgumentParser,
    ArgumentDefaultsHelpFormatter,
    RawDescriptionHelpFormatter,
)
import pandas as pd

DATE_REGEX = [
    '([0-9][0-9]?)([A-Z][a-z]+)([0-9]{2})_([0-9]{4})$',
    '([0-9][0-9]?)_([0-9][0-9]?)_([0-9]{2})_([0-9]{4})([AP]M)$',
]

MONTHS = {
    'january': 1,
    'februray': 2,
    'march': 3,
    'april': 4,
    'may': 5,
    'june': 6,
    'july': 7,
    'august': 8,
    'september': 9,
    'october': 10,
    'november': 11,
    'december': 12,
}

def remove_extension(fname):
    return re.sub('( \([0-9]+\))?\.txt$', '', fname)

def convert_month(month):
    for name, number in MONTHS.items():
        if name.startswith(month):
            return number

def convert_twelve_hour(time):
    if len(time) == 6:
        hours = time[0:2]
        minutes = time[2:4]
        meridiem = time[4:]
    else:
        hours = time[0]
        minutes = time[1:3]
        meridiem = time[3:]

    if meridiem == 'PM' and hours != '12':
        hours = str((int(hours) + 12) % 24)

    return hours + minutes

def process_filename_time(fname):

    if re.search(DATE_REGEX[0], fname):
        dmatch = re.search(DATE_REGEX[0], fname)
        day = dmatch.group(1)
        month = convert_month(dmatch.group(2).lower())
        year = '20' + dmatch.group(3)
        time = dmatch.group(4)
    elif re.search(DATE_REGEX[1], fname):
        dmatch = re.search(DATE_REGEX[1], fname)
        day = dmatch.group(2)
        month = dmatch.group(1)
        year = '20' + dmatch.group(3)
        time = convert_twelve_hour(dmatch.group(4))
    else:
        raise Exception(f'Unable to detect time: {fname}')

    dt = f'{year}-{month}-{day} {time}'
    dt = datetime.strptime(dt, '%Y-%m-%d %H%M') 

    return dmatch.span()[0], dt

def is_valid_name(fname):
    """Checks if a file name is valid. The number of underscores confirms validity."""

    if ((re.search(r'[0-9]{4}(\.txt)?$', fname) or
         re.search(r'[0-9] \([0-9]\)(\.txt)?$', fname) or
         re.search(r'[0-9]{4}[AP]M(\.txt)?$', fname) or
         re.search(r'[0-9]{4}[AP]M \([0-9]\)(\.txt)?$', fname)) and
         fname.count('_') > 2):
        return True
    else:
        return False

def parse_file(fname):
    """
    Parse a file name into its respective parts.

    Parameters
    ----------

    fname: str
        the file name

    Output
    ------

    participant: str
        participant name
    tname: str
        test name
    time: datetime
        test date and time
    """

    fname = remove_extension(fname)
    pmatch = re.match('([A-Za-z0-9]+)_', fname)
    participant = pmatch.group(1)
    tbegin = pmatch.span()[1]
    dbegin, time = process_filename_time(fname)
    tend = dbegin - 1
    tname = fname[tbegin:tend]

    return participant, tname, time

def process_directory(dname):
    """
    Parse the files within a directory into their respective parts.

    Parameters
    ----------

    dname: str
        the directory name

    Output
    ------

    df: pd.DataFrame
        a data frame containing all the file information
    invalid_files: list of str
        lists the invalid files
    """

    results = {
        'file_name': [],
        'participant': [],
        'test': [],
        'date': [],
    }

    invalid_files = []
    dname = Path(dname).resolve()
    directory_files = [x.name for x in dname.iterdir() if x.is_file()]
    for fname in directory_files:
        fname = fname.replace('-', '_')

        if is_valid_name(fname):
            participant, tname, time = parse_file(fname)
            results['file_name'].append(fname)
            results['participant'].append(participant)
            results['test'].append(tname)
            results['date'].append(time)
        else:
            invalid_files.append(fname)

    return pd.DataFrame(results), invalid_files

def get_parser():
    """Define parser object"""

    epilog = """
This program lists all files within a directory and parses the participant
name, test name, and date from the file name. The file names are expected
to have this syntax:

{participant}_{test_name}_{date}

The date can have 2 formats:

%d%M%y %H%M
%m%d%y %H%M([AP]M)?

The first date format is the most common.

Here are some example usage:

    Display the hep and exit:

        cli_print_test --help

    List all the tests within the inclusive range 2020-1-15 to 2020-1-23:

        cli_print_test --date_range 2020-1-15 2020-1-23 --directory /path/to/some/directory

    List all the tests within the inclusive range 2020-1-15 to 2020-1-23 for participant MCWA004:

        cli_print_test --date_range 2020-1-15 2020-1-23 --participant MCWA004 --directory /path/to/some/directory

    List all the tests for participant MCWA004:

        cli_print_test --participant MCWA004 --directory /directory/path

    List all the 'Reading(2)' tests:

        cli_print_test --test 'Reading(2)' --directory /directory/path

    Display missing tests for participant MCWA004 within inclusive range 2020-1-15 to 2020-1-23:

        cli_print_test --missing_tests --participant MCWA004 --date_range 2020-1-15 2020-1-23 --directory /directory/path

    Display all the invalid files found and immediately exit:

        cli_print_test --directory /directory/path --list_invalid_files
"""

    parser = ArgumentParser(
        description='list some test infomration for a directory',
        epilog=epilog, 
        formatter_class=RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--directory',
        action='store', 
        required=True,
        help='read the test files within this directory'
    )

    parser.add_argument(
        '--date_range', 
        action='store', 
        nargs=2,
        help='display results within this date range'
    )
    
    parser.add_argument(
        '--participant', 
        action='store',
        help='display results for this participant only'
    )

    parser.add_argument(
        '--test', 
        action='store',
        help='list only information regarding this test.'
    )

    parser.add_argument(
        '--missing_tests', 
        action='store_true',
        help='list only missing tests'
    )

    parser.add_argument(
        '--list_invalid_files', 
        action='store_true',
        help='list the invalid files and exit the program',
    )

    return parser

def main():
    parser = get_parser()
    args = parser.parse_args()

    directory = args.directory
    dates = args.date_range
    participant = args.participant
    test = args.test
    missing_tests = args.missing_tests
    list_invalid_files = args.list_invalid_files

    df, invalid_files = process_directory(directory)

    if list_invalid_files:
        print(f'Here are the invalid files:')

        for invalid_file in invalid_files:
            print(f'\t{invalid_file}')

        sys.exit()

    all_test = set(df['test'])

    if dates is not None:
        df = df.loc[df['date'].ge(dates[0]) & df['date'].le(dates[1])]

    if participant is not None:
        df = df.loc[df['participant'].eq(participant)]

    if test is not None:
        df = df.loc[df['test'].eq(test)]

    if missing_tests:
        print('Here are the missing tests:')
        missing = all_test.difference(df['test'])
        for one_test in missing:
            print('\t{missing}')

        sys.exit()

    print(df.sort_values('date', ignore_index=True).to_string())
if __name__ == '__main__':
    main()

