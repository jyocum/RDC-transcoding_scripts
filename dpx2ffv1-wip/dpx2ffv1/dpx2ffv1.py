#!/usr/bin/env python3

import sys
if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")

def main():
    from dpx2ffv1 import dpx2ffv1mainfunc
    dpx2ffv1mainfunc.dpx2ffv1_main()

if __name__ == "__main__":
	main()