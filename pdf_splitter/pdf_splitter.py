# -*- coding: utf-8 -*-

"""Main module."""
from PyPDF2 import PdfFileWriter, PdfFileReader
import glob
import os
import sys
import argparse

class Splitter():
    def __init__(self, input_folder):
        self.input_folder = input_folder

    def split(self):
        pdf_files = glob.glob(os.path.join(self.input_folder, "*.pdf"))
        out_dir = os.path.join(self.input_folder, "out")
        os.makedirs(out_dir, exist_ok=True)
        for file_name in pdf_files:
            basename = os.path.basename(file_name)
            inputpdf = PdfFileReader(open(file_name, "rb"))
            if inputpdf.getNumPages() < 2:
                continue
            for i in range(inputpdf.numPages):

                outfile = os.path.join(out_dir, basename[:-4] + "_%s.pdf" % i)
                output = PdfFileWriter()
                output.addPage(inputpdf.getPage(i))
                with open(outfile, "wb") as stream:
                    output.write(stream)
def main():
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument('--input_dir', '-input_dir',
                        help="Input Directory where pdf files", type=str, required=True)
    ARGUMENTS = PARSER.parse_args()
    input_dir = ARGUMENTS.input_dir
    splitter = Splitter(input_dir)
    splitter.split()

if __name__ == "__main__":

    sys.exit(main()) 